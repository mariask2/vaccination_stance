# -*- coding: utf-8 -*-

"""
This is a script for extracting the debate post from the site mumsnet.

Downloading of threads is done manually as follows
Go to: https://www.mumsnet.com/Talk
Click on: Topic A-Z
Click on the topic you're interested in and then on the thread you're interested in
IMPORTANT 1: If the thread has more than 100 posts, you need to click on "Show 100 messages" do get all messages.
Save the page, and then click 'next' and save it as well, and continue until the entire thread is downloaded
Pages for one thread will all be given the same default name, so you need to rename them manually. The files need t have the suffix .html
to be considered by the script.

IMPORTANT 2:The script relies on that pages with earlier posts have been saved on the computer before pages with later posts, since the removal of citations from previous posts relies on ordering the files in a debate thread according to the date they were save. This is not very robust, and should be changed if the script is to be used in some other for any other purpose.

For running the script, you need to give the directory where you have downloaded the data as an argument E.g. (if the name of the directory is mumsnet):
python extract_mumsnet.py mumsnet

For the script to be run, NLTK must be installed and the english tokenizer downloaded, and jusText must be installed.

"""

import os
import justext
import glob
import re
import random
import sys
import nltk
import string

sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
sentence_merged = re.compile(".*\.[A-Z].*")
sentence_tilde = re.compile(".*\.\~.*")

"""
Fixes for the sentence segmentation for messy text
"""
def pre_processing_fixes(text):
    if sentence_merged.match(text):
        # Should do a regex replace here, but am lazy
        for st in string.ascii_uppercase:
            text = text.replace("." + st, ". " + st)
    if sentence_tilde.match(text):
        # Should also combine into one regex
        text = text.replace(".~", ". ")
    return text

def get_only_alpha(text):
    return ''.join([i if i.isalpha() else '' for i in text]).lower()

def extract_discussion(output_directory_name, downloaded_debate_directory):

    # Create the directory where to put the files that are to be annotated
    if not os.path.exists(output_directory_name):
        os.makedirs(output_directory_name)
        
    # Find all html files
    files = glob.glob(os.path.join(downloaded_debate_directory, "*.html"))
    files.sort(key=lambda x: os.path.getmtime(x)) # rely on that pages with older posts are saved first
    print("Nr of files ", len(files))
        
    result = []
    nr_of_posts = 0
    nr_of_authors = 0 # Not unique ones
    nr_of_ids = 0 # Not unique ones
    unique_authors = set()
    ids = set()
    last_id = None
    current_author = None
    current_id = "original-first-post"
    
    title_row = [["Author", "Nr", "Classification", "Text", "Annotation notes", "Id", "First token", "Debate thread"]]
    sentence_set = set()
    paragraph_list = []
    sentence_list = []
    replaced_paragraphs = 0
    replaced_paragraphs_ids = []
    for f in files:
        print(f)
        f = open(f)
        lines = f.readlines()
        f.close()
        current_result_row = []
        for i, line in enumerate(lines):
            if '<div class="talk-post  message">' in line or '<div class="talk-post  original-first-post  message">' in line:
                if '<div class="talk-post  original-first-post  message">' in line:
                    current_id = "original-first-post"
                    nr_of_ids = nr_of_ids + 1
                raw_text = lines[i+1]
                if "<strong>" in raw_text: # To remove citations from previous authors
                    matches = re.findall('<strong>.*?<.*?strong>', raw_text)
                    for el in matches:
                        match = el.replace("<strong>","").replace("</strong>","")
                        if len(match.split(" ")) > 3: #and get_only_alpha(match) in sentence_set:
                            raw_text = raw_text.replace(match, "_CITATION_PREVIOUS_POST_")
                            #print(raw_text)
                if "&quot;" in raw_text: # To remove citations from previous authors
                    matches = re.findall('&quot;.*?&quot;', raw_text)
                    for el in matches:
                        match = el.replace("&quot;","")
                        if len(match.split(" ")) > 3: #and get_only_alpha(match) in sentence_set:
                            raw_text = raw_text.replace(match, "_CITATION_PREVIOUS_POST_")
                               
                paragraphs = justext.justext(raw_text.replace("<", " <").replace(">", "> ").replace("*", ".<br><br>"), justext.get_stoplist("English"))
                # some authors use * to express start of citation

                old_text = " _NEWLINE_ _NEWLINE_ _NEWLINE_ _NEWLINE_ ".join([paragraph.text for paragraph in paragraphs]).strip()
                text_to_include = []
                for  paragraph in paragraphs: #Only include new text, to remove citations
                    contains_new_text = False
                    if (get_only_alpha(paragraph.text) not in paragraph_list and get_only_alpha(paragraph.text) not in sentence_list) \
                        or "_CITATION_PREVIOUS_POST_" in paragraph.text: # only then can it be considered as new text
                        sentences = sent_detector.tokenize(pre_processing_fixes(paragraph.text))
                        for sentence in sentences:
                            if get_only_alpha(sentence) not in sentence_list:
                                contains_new_text = True
                    if contains_new_text:
                         text_to_include.append(paragraph.text)
                    else:
                        text_to_include.append("_CITATION_PREVIOUS_POST_PARAGRAPH")
                if len(text_to_include) != 0:
                    text = " _NEWLINE_ _NEWLINE_ _NEWLINE_ _NEWLINE_ ".join(text_to_include).strip()
                else: # if there is no new text, than take the enire post
                    text = " _NEWLINE_ _NEWLINE_ _NEWLINE_ _NEWLINE_ ".join([paragraph.text for paragraph in paragraphs]).strip()
                if old_text != text:
                    replaced_paragraphs = replaced_paragraphs + 1
                    replaced_paragraphs_ids.append(current_id)

                for el in paragraphs:
                    paragraph_list.append(get_only_alpha(el.text))
                    if len(paragraph_list) > 50:
                        del paragraph_list[0] # only keep the most recent posts to compare with for citations
                    sentences = sent_detector.tokenize(pre_processing_fixes(el.text))
                    for sentence in sentences:
                        sentence_list.append(get_only_alpha(sentence))
                        if len(sentence_list) > 200:
                            del sentence_list[0] # only keep the most recent posts to compare with for citations

                    
                sentences = sent_detector.tokenize(pre_processing_fixes(text))
                for el in sentences:
                    sentence_set.add(get_only_alpha(el))
                nr_of_posts = nr_of_posts + 1
                current_result_row.append(str(nr_of_posts))
                current_result_row.append("")
                current_result_row.append(text.replace('\n', ' ').replace('\r', '').replace('\t', ' '))
                current_result_row.append("")
                current_result_row.append(current_id)
                current_result_row.append(text.split(" ")[0])
                current_result_row.append(str(f.name))
                last_id = current_id
            if '<span class="nickname">' in line:
                nr_of_authors = nr_of_authors + 1
                if '<a rel="nofollow"' not in lines[i+1]:
                    current_author = lines[i+1].split('title="')[1].split('" class="')[0]
                else:
                    current_author = lines[i+1].split('Profile?nick=')[1].split('" target="_blank"')[0]
                unique_authors.add(current_author)
                current_result_row.append(current_author)

                #  Here, a new post is started   
            if '<div id="' and '" class="post ">' in line:
                current_id = line.split('<div id="')[1].split('" class="post ">')[0]
                nr_of_ids = nr_of_ids + 1
                ids.add(current_id)
                if current_result_row != []: # Save the old post gathered, and start gathering info for a new one
                    result.append(current_result_row)
                    current_result_row = []
        result.append(current_result_row)        

    random.shuffle(result)
    results_with_title_row = title_row + result
    nr_of_final_lines = 0
    nr_of_final_lines_filtered = 0
    previous_lines = set()
    outputfile = open(os.path.join(output_directory_name, "extracted_full_information.txt"), "w")
    outputfile_no_author = open(os.path.join(output_directory_name, "extracted_for_annotator.txt"), "w")
    outputfile_no_author_filtered = open(os.path.join(output_directory_name, "extracted_for_annotator_filtered.txt"), "w")
    outputfile_filtered = open(os.path.join(output_directory_name, "extracted_full_information_filtered.txt"), "w")
    for el in results_with_title_row:
        # Don't include post where justext couldn't find any content or withdraw or deleted ones
        if el[3] not in previous_lines: # No duplicates allowed
            if el[3].strip() != "" and not "Message deleted by Mumsnet" in el[3] or "Message withdrawn at" in el[3] or "please remember our guidelines" in el[3]: 
                outputfile.write("\t".join(el[0:8]))
                outputfile.write("\n")
                outputfile_no_author.write("\t".join(el[1:7])) # Hide some of the information for the annotator
                outputfile_no_author.write("\n")
                nr_of_final_lines = nr_of_final_lines + 1
                previous_lines.add(el[3])
                if "vacc" in el[3].lower() or "vax" in el[3].lower() or "jab" in el[3].lower() or "immunis" in el[3].lower() or "immuniz" in el[3].lower():
                    outputfile_filtered.write("\t".join(el[0:8]))
                    outputfile_filtered.write("\n")
                    outputfile_no_author_filtered.write("\t".join(el[1:7])) # Hide some of the information for the annotator
                    outputfile_no_author_filtered.write("\n") # Hide some of the information for the annotator
                    nr_of_final_lines_filtered = nr_of_final_lines_filtered + 1

    outputfile.close()
    outputfile_no_author.close()
    outputfile_filtered.close()
    outputfile_no_author_filtered.close()

    print("nr_of_posts", nr_of_posts) 
    print("nr_of_authors", nr_of_authors)
    print("unique_authors", len(unique_authors))
    print("result", len(results_with_title_row))
    print("nr_of_final_lines", nr_of_final_lines)
    print("nr_of_ids", nr_of_ids)
    print("ids", len(ids))
    print("replaced_paragraphs", replaced_paragraphs)
    print("nr_of_final_lines_filtered", nr_of_final_lines_filtered)
    
    """
    # Code for writing id:s of paragraphs that were replace. Should not be needed.
    replace_file = open(os.path.join(output_directory_name, "replaced_paragraphs_ids"), "w")
    for el in replaced_paragraphs_ids:
        replace_file.write(el + "\n")
    replace_file.close()
    """
    
def run():
    if len(sys.argv) < 2:
        sys.exit("You need to give the directory name of the html files that have been downloaded from mumsnet as an argument")
    downloaded_debate_directory = sys.argv[1]
    print("Will look in the directory " + downloaded_debate_directory + " for mumsnet debate files. (Will only consider .html files.)")

    output_directory_name = "extracted"

    print("The extracted data will be written in the directory: " + output_directory_name)
    extract_discussion(output_directory_name, downloaded_debate_directory)

if __name__ == '__main__':
   run()

