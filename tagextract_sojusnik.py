#!/usr/bin/python
'''Extract text lines by tags.

- Read in a text file in markdown or zim wiki syntax with tags denoted by @ (e.g. @tag1).
- Given a tag name <tag>, extract all text lines associated with <tag>.
- Tag association is defined by tab levels:
    - The lines where <tag> is found are included.
    - Looking backwards, lines with same tab level or 1 higher level are included, unless
      encounters another tag definition line.
    - Looking forwards, lines with same or lower tab levels are included.
    - Searching stops at headings (e.g. ## heading in markdown or === heading === in zim).
    - Searching stops at image definitions (e.g. ![](url) in markdown or {{path}} in zim).

- Input file needs to have rather strict tab useages.


# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-03-23 17:17:07.
'''

import sys, os
import re
import argparse
from lib import tools
from lib import textparse




class TagFinder(object):

    def __init__(self, syntax='markdown'):
        self.syntax=syntax
        self.tp=textparse.TextParser(syntax)

        self._checkbox_re=re.compile('''
        (
          \\[
            [* x]
          \\]
          (.*)
        )
        ''', re.L | re.X | re.M)


    def searchUp(self,lines,tag,lineidx,lvl):
        result_idx=[]

        for ii in range(lineidx,-1,-1):
            lineii=lines[ii]

            #-----------------Include checkbox-----------------
            ischeck=self._checkbox_re.findall(lineii)
            if len(ischeck)>0:
                result_idx.append(ii)
                continue

            #---------Include img def lines and move on---------
            if self.tp.isImg(lineii):
                result_idx.append(ii)
                continue

            #-------------------Tag in line?-------------------
            taginline=self.tp.findTags(lineii)
            if len(taginline)>0 and tag in taginline:
                linecp=lineii
                for tt in taginline:
                    linecp=linecp.replace(tt,u'')
                if not self.tp.isEmpty(linecp):
                    result_idx.append(ii)
                    continue
                else:
                    continue

            #--------Include and stop at any heading-----------
            isheader=self.tp.isHeader(lineii)
            if isheader:
                result_idx.append(ii)
                return result_idx

            #---------Include empty lines and move on---------
            if self.tp.isEmpty(lineii):
                return result_idx


        return result_idx


    def searchDown(self,lines,tag,lineidx,lvl):
        result_idx=[]

        for ii in range(lineidx+1,len(lines)):
            lineii=lines[ii]
            isheader=self.tp.isHeader(lineii)

            if self.tp.isEmpty(lineii):
                result_idx.append(ii)
                return result_idx

            if self.tp.isImg(lineii):
                result_idx.append(ii)
                continue
            if isheader:
                return result_idx

        return result_idx




    def findAllTags(self,lines):

        #----------------Loop through lines----------------
        tagdict={}
        for ll, tt in enumerate(lines):
            tt, tabnum=self.tp.space2tab(tt)
            tagll=self.tp.findTags(tt)

            if len(tagll)>0:
                for tagii in tagll:
                    taglvl=tabnum
                    if tagii in tagdict:
                        tagdict[tagii].append([ll,taglvl])
                    else:
                        tagdict[tagii]=[[ll,taglvl]]

        return tagdict




    #-----------------Extract text lines by tag-----------------
    def extractTag(self,text,tag,verbose=True):
        '''Extract text lines by tag

        text, tag, synatx 
        '''
        #--------------------Preprocess--------------------
        text = re.sub("\r\n|\r", "\n", text)
        lines=text.split('\n')
        lines=[ii+'\n' for ii in lines]

        #------------------Find all tags------------------
        tagdict=self.findAllTags(lines)

        #-------------Preprend @ if not given-------------
        if len(self.tp.findTags(tag))==0:
            tag='@%s' %tag

        #-------------Extract line idx by tag------------------
        result_idx=[]
        if tag not in tagdict:
            print('# <tagextract>: Your given tag "%s" is not found in input file.' %tag)
            print('# <tagextract>: Tags found from file:')
            for tt in tagdict.keys():
                print(tt)
            return

        for ii in tagdict[tag]:
            lineidx,lvl=ii
            linesabove=self.searchUp(lines,tag,lineidx,lvl)
            linesbelow=self.searchDown(lines,tag,lineidx,lvl)
            linesabove.reverse()

            if not set(linesabove).issubset(set(result_idx)):
                result_idx.extend(linesabove)
            if not set(linesbelow).issubset(set(result_idx)):
                result_idx.extend(linesbelow)

        #-----------------Get lines by idx-----------------
        result_idx=list(set(result_idx))
        result_idx.sort()
        result_lines=[lines[ii] for ii in result_idx]
        result_lines=self.tp.leftJust(result_lines)
        result_lines=u''.join(result_lines)

        return result_lines






#-------------------Extract tagged texts from file.-------------------
def main(filein,fileout,tag,syntax='markdown',verbose=True):
    '''Extract tagged texts from file.

    filein
    '''

    text=tools.readFile(filein,verbose)
    if verbose:
        print('# <tagextract>: Extracting tagged lines...')
    tagfinder=TagFinder(syntax)
    newtext=tagfinder.extractTag(text,tag)
    if newtext is not None:

        headersym='# ' if syntax=='markdown' else '====='
        header='Summary of tag: %s' %tag
        header='%s %s %s' %(headersym, header, headersym)
        newtext=header+'\n\n'+newtext

        tools.saveFile(fileout,newtext,verbose)

        return



#-----------------------Main-----------------------
if __name__=='__main__':

    parser=argparse.ArgumentParser(description=\
            'Extract text lines by tags')

    parser.add_argument('file',type=str,help='Input text file')
    parser.add_argument('tag',type=str,help='Tag to extract')
    parser.add_argument('-o','--out',type=str,\
            help='Optional output file name.')

    #syntax=parser.add_mutually_exclusive_group(required=True)
    '''
    parser.add_argument('-m','--markdown', action='store_true',\
            help='Input text uses markdown syntax.')
    parser.add_argument('-z','--zim', action='store_true',\
            help='Input text uses zim wiki syntax.')
    '''

    parser.add_argument('-v','--verbose',action='store_true',\
            default=True,\
            help='Show processing messages.')

    try:
        args=parser.parse_args()
    except:
        sys.exit(1)

    FILEIN=os.path.abspath(args.file)
    TAG=args.tag
    if not args.out:
        FILEOUT='%s_tag-%s.txt' %(os.path.splitext(args.file)[0], TAG)
    else:
        FILEOUT=args.out
    FILEOUT=os.path.abspath(FILEOUT)

    '''
    if args.markdown:
        SYNTAX='markdown'
    elif args.zim:
        SYNTAX='zim'
    '''

    main(FILEIN,FILEOUT,TAG,'zim',args.verbose)


