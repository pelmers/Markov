#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
generator.py
Generate random responses from a prompt after analyzing a text
'''

# Peter Elmers
# 11/21/10

import sys
import os
import os.path
from random import choice, randint
# defaultdict is convenient for building sets
from collections import defaultdict
# handles downloading texts from internet
import urllib2
# compatability for both 2.4+ and 3.x
if sys.version_info[0] < 3:
    input = raw_input
    range = xrange
    
USAGE = """\
Usage: generator.py [FILE]
Parse each FILE and allow sentences to be generated.
With multiple files, parse all and combine them.
If no FILE is given, prompt to download an ebook from Project Gutenberg.

Options:
-h, --help          Print this message and exit
-u, --usage         Print this message and exit
"""

def menu():
    '''
    Returns the number of the user's choice
    '''
    print('''\n    1) Generate sentences using parsed books
    2) Download a book from the Internet (gutenberg.org)
    3) Clear parsed books
    4) Exit''')
    choice = None
    
    while not choice:
        choice = input("Choice: ")
        try:
            choice = int(choice)
        except ValueError:
            print("Invalid input")
            continue
        if not (choice > 0 and choice < 5):
            print("Choice out of range")
            continue
    return choice

def tokenize(text):
    '''
    From a text string, make a list of all words (lowercased).
    Try to take into account titles (e.g. Mr.) and names (e.g. Peter)
    Return list of words and list of titles found
    '''
    num_chars = [str(i) for i in range(10)]
    symbols = ['.','?','!',',','\'','-']
    valid_chars = set(num_chars+symbols)
    num_chars = set(num_chars)
    symbols = set(symbols)
    tokens = []
    names = set(['I'])
    titles = set(['Mr.','M.','Mrs.','Dr','Ms.','Rep','Sen.','Gen.','St.'])
    # each line becomes a list element
    text = text.split('\n')
    for i in range(len(text)):
        # append double-quote to each line, lets us know it is not a name
        # does not affect tokenization, " is stripped from result
        # most useful when parsing poems, as there are many new lines
        text[i] = '"'+text[i]
    # done with that, now rejoin text
    text = ' '.join(text)
    # now split on whitespace
    split_text = text.split()
    for i, w in enumerate(split_text):
        # avoid all capital words, instead just keep first capital letter
        if all(c.isupper() for c in w[:-1]):
            w = w[0] + ''.join([c.lower() for c in w[1:]])
        # if first character is uppercased, it may be a title or name
        if w[0:1].isupper():
            # if it is capitalized and short and there is a period at the end, it should be a title
            if len(w) < 4 and w[-1] == '.' and w.count('.') == 1 and w not in names and sum(1 for i in w if i.isalpha()) > 0:
                titles.add(w)
            if i != 0:
                if w in names:
                    # already detected as name
                    tokens.append(unicode(w))
                    continue # go to next word
                # make sure it is not start of sentence and not after a title
                elif not (split_text[i-1][-1] in ('.','!','?','"') and
                          split_text[i-1] not in titles):
                    # previous word ended sentence
                    # strip invalid characters
                    w = ''.join([c for c in w if (c.isalpha() or c in valid_chars)])
                    tokens.append(unicode(w))
                    names.add(unicode(w))
                    continue
            elif i == 0:
                # strip invalid characters
                w = ''.join([c for c in w if (c.isalpha() or c in valid_chars)])
                tokens.append(unicode(w))
                names.add(unicode(w))
                continue
        # make sure that it is not just symbols
        if sum(1 for c in w if c.isalpha() or c in num_chars) > 0:
            # strip invalid characters
            w = ''.join([c for c in w if (c.isalpha() or c in valid_chars)])
            tokens.append(unicode(w.lower()))
    return tokens, list(titles)

def build_sets(tokens, length=2):
    '''
    From a list of tokens, build sets of relations for each phrase
    Phrase length is controlled by optional length argument (default 2)
    Returns a dictionary of sets, using tuples as keys
    '''
    sets = defaultdict(list)
    token_length = len(tokens) # we don't need to run len() every time
    for i, w in enumerate(tokens):
        # we cannot build anything if it is still at the first part of the list
        if i+1 < length:
            continue
        # stop one before the end
        if i+1 == token_length:
            break
        # generate phrase key from length argument
        key = [tokens[i-n] for n in range(1,length)]
        key.append(w)
        # convert key to tuple for use in dict, append next word
        sets[tuple(key)] += [tokens[i+1]]
    # convert back to regular dict when returning
    return dict(sets)

def tokenize_from_gutenberg(bn):
    '''
    Downloads given book number from gutenberg.org
    Return tokens and titles obtained from the book and url of book
    If failed, returns -1,-1,-1
    '''
    f = None
    bnsplit = [i for i in str(bn)]
    # gutenberg.org directory structure is based off book number
    # ex: book no. 1901 is found at http://www.gutenberg.org/dirs/1/9/0/1901/
    url = "ftp://ftp.ibiblio.org/pub/docs/books/gutenberg/"
    url1 = "http://www.gutenberg.org/cache/epub/%s.txt.utf8" % (bn)

    try:
        f = urllib2.urlopen(url1, 'rU')
        print(url1 + " found")
        correct_url = url1
    except:
        pass

    if not f:
        # try these if the simple directory doesn't work
        for i, n in enumerate(bnsplit):
            if i != len(bnsplit) - 1:
                url += n + '/'
            else:
                url += ''.join(bnsplit) + '/'
        urls = [url for i in range(4)]
        # possible line endings for the file
        urls[0] += "%s.txt" % (bn)
        urls[1] += "%s-8.txt" % (bn)
        urls[2] += "%s-7.txt" % (bn)
        urls[3] += "%s-0.txt" % (bn)
        for u in urls:
            try:
                f = urllib2.urlopen(u, 'rU')
                print(u + " found.")
                correct_url = u
                break
            except urllib2.URLError:
                pass
            except urllib2.HTTPError:
                pass
    if not f:
        return -1, -1, -1
    book = f.read()       
    # tokenize up to END OF book
    tokens, titles = tokenize(book[:book.find(" END OF")])
    return tokens, titles, correct_url

def respond(sets, titles, prompt, sentences=3, sent_breaks=1):
    '''
    Responds to a given prompt using given sets and titles
    Number of sentences controls response length
    Length of each returned sentence does not exceed 120 words
    sent_breaks, if not 0, starts sentences on new lines
    0 means no line breaks and -1 breaks by sentence
    Returns response as a string
    '''
    if len(prompt) == 0:
        # a few common choices
        prompt = choice(['It is','It was'])
    key_len = len(str(sets.keys()[0]).split())
    res_list = ' '.join(tuple(prompt.split())[:key_len]).split()
    sentence_length = key_len
    sentence_indices = []
    while 1:
        # generate prompt based off last entries in result
        prompt = tuple(res_list[-key_len:])
        # increase word count for this sentence
        sentence_length += 1
        # make sure first word of a sentence is capitalized
        if sentence_length == 1:
            res_list[-1] = res_list[-1].capitalize()
        # tries to avoid all-capital abbrev.
        if not all((c.isupper()) for c in res_list[-1] if c.isalpha()):
            if res_list[-1] not in titles: # a title is not end of sentence
                if res_list[-1][-1] in ('.','!','?'):
                    sentences -= 1
                    sentence_length = 0
                    # keep track of where each sentence ends
                    sentence_indices.append(len(res_list)-1)
                # we should not infinite-loop if no periods found
                elif sentence_length >= 120:
                    sentences -= 1
                    sentence_length = 0
                    sentence_indices.append(len(res_list)-1)
                if sentences <= 0:
                    break
        if prompt in sets:
            res_list.append(choice(sets[prompt]))
            continue
        done = False
        candidates = []
        # FIXME: this is a horrible way to prioritize, instead
        # the closest match must ALWAYS be chosen! otherwise it's gibberish!
        for k in sets:
            for i in range(key_len-1):
                # phrases with more than 1 match will have a higher chance
                if str(prompt[i]) == k[i]:
                    candidates.append(k)
        if candidates:
            done = True
            res_list.append(choice(sets[choice(candidates)]))
        # we still haven't found a match
        if done == False:
            # just choose a random one
            res_list.append(choice(sets[choice(sets.keys())]))

    if sent_breaks == 0:
        response = ' '.join(res_list)
    else:
        # with this value, break lines on new sentences
        response = []
        for index, number in enumerate(sentence_indices):
            if index == 0:
                response.append(' '.join(res_list[:number+1]))
            else:
                response.append(' '.join(res_list[sentence_indices[index-1]+1:number+1]))

        response = '\n'.join(response)
    return response

def main():
    '''
    Simple command-line program which takes texts as filename arguments
    If no valid texts are found, will prompt to download text from internet
    '''
    tokens = []
    sets = {}
    titles = []
    f = tg = None
    done = False
    # run through arguments to see if user asks for help
    for arg in sys.argv[1:]:
        if arg in ('--help','-h','-u','--usage'):
            print(USAGE)
            return
            
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            print("Parsing %s..." % arg)
            f = open(arg, 'rU')
            new_tokens, new_titles = tokenize(f.read())
            tokens += new_tokens
            titles += new_titles
            new_set = build_sets(tokens)
            # dict.update not used because that overwrites existing keys
            for key in new_set:
                if key not in sets:
                    sets[key] = new_set[key]
                else:
                    sets[key] += new_set[key]
            f.close()

    while done == False:
        choice = menu()
        if choice == 1:
            if len(sets) == 0:
                print("No books parsed")
                continue
            prompt = input('Hey! Could I have a prompt? ')
            count = input('How many sentences? ')
            try:
                count = int(count)
            except ValueError:
                # not an integer
                print("Invalid input, generating 4 sentences instead.")
                count = 4
            if count == 0:
                count += 1
            print('\n'+respond(sets, set(titles), prompt, count))
            continue
        elif choice == 2:
            r = input("Which? (number greater than 11) ")
            try:
                r = int(r)
                if not (10 < r):
                    raise IndexError
                book_no = r
            except:
                print("Unrecognized input, using a random one instead...")
                book_no = randint(11,34110)
            tg, new_titles, url = tokenize_from_gutenberg(book_no)
            if tg == -1:
                print("This book seems to not be available.")
                continue
            # titles was a set type to make 'in' faster, but list has +=
            titles = list(titles)
            titles += new_titles
            new_set = build_sets(tg, length=2)
            
            tg = ' '.join(tg)
            title_end = tg.find("this ebook")
            if title_end == -1:
                title_end = tg.find("This ebook")
            if title_end == -1:
                title_end = tg.find("copyright")
            if title_end == -1:
                title_end = tg.find("Copyright")
            print('Fetched book number %s' % (book_no))
            print(tg[:title_end])
                
            for key in new_set:
                if key not in sets:
                    sets[key] = new_set[key]
                else:
                    sets[key] += new_set[key]
            titles = set(titles)
            
            save_book_name = input("\nEnter a filename to save ('no' to not save): ")
            if save_book_name == '':
                print("No save name given, discarding book...")
            # if user does not want to throw it away
            elif save_book_name.lower() not in ('no','false','discard','n'):
                if not os.path.isdir('books'):
                    os.mkdir('books')
                save = open(os.path.join('books', save_book_name), 'w')
                save.write(urllib2.urlopen(url, 'rU').read())
                print("%s saved." % (save_book_name))
            else:
                print("Book was not saved.")
            continue



        elif choice == 3:
            tokens = []
            sets = {}
            titles = []
            print("Books cleared.")
            continue

        elif choice == 4:
            done = True
        
if __name__ == '__main__':
    # yay!
    main()
