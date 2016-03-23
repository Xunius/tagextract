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




class TagFinder(object):

    def __init__(self, syntax='markdown'):
        self.syntax=syntax
        self.defSyntax()
        self.tab_width=4


    def defSyntax(self):

        self._tab_re=re.compile('^(\\s+)(\\S.*)', re.X | re.L | re.M)
        self._tag_re=re.compile('@(?=\\S)(.+?)\\b', re.L | re.X | re.M)
        self._ws_only_line_re = re.compile(r"^[ \t]+$", re.M)

        if self.syntax=='markdown':

            self._img_re=re.compile('^(.*)!\\[(.+?)\\]\\((.+?)\\)', re.M | re.L)
            _h_re_base = r'''
            (^(.+)[ \t]*\n(=+|-+)[ \t]*\n+)
            |
            (^(\#{1,6})  # \1 = string of #'s
            [ \t]%s
            (.+?)       # \2 = Header text
            [ \t]*
            (?<!\\)     # ensure not an escaped trailing '#'
            \#*         # optional closing #'s (not counted)
            \n+
            )
            '''
            self._h_re = re.compile(_h_re_base % '*', re.X | re.M)

        elif self.syntax=='zim':

            self._img_re=re.compile('^(.*)\\{\\{(.+?)\\}\\}(.*)$', re.M | re.L)
            _h_re_base = r'''
                ^(\={1,6})  # \1 = string of ='s
                [ \t]%s
                (.+?)       # \2 = Header text
                [ \t]*
                \1
                \n+
                '''
            self._h_re = re.compile(_h_re_base % '*', re.X | re.M)

        return



    def space2tab(self,text):

        #roundint=lambda x: int(x+1) if x-int(x)>=0.5 else int(x)
        m=self._tab_re.match(text)
        if m:
            spc=m.group(1)
            spclen=spc.count(' ')+self.tab_width*spc.count('\t')
            #num=roundint(spclen/4.)
            #return '%s%s' %('\t'*num, m.group(2)), num
            return '%s%s' %(' '*spclen, m.group(2)), spclen/float(self.tab_width)
        else:
            return text, 0


    def isHeader(self,text):
        if self._h_re.match(text):
            return True
        else:
            return False


    def isEmpty(self,text):
        if len(text)==0 or self._ws_only_line_re.match(text)\
                or text=='\n':
            return True
        else:
            return False


    def isImg(self,text):
        m=self._img_re.match(text)
        if m:
            return True
        else:
            return False
        

    def searchUp(self,lines,tag,lineidx,lvl):
        result_idx=[lineidx]
        sameblock=True

        for ii in range(lineidx-1,-1,-1):
            lineii=lines[ii]
            tablvl=self.space2tab(lineii)[1]
            isheader=self.isHeader(lineii)

            #---------Include empty lines and move on---------
            if self.isEmpty(lineii):
                result_idx.append(ii)
                continue
            #---------Include img def lines and move on---------
            if self.isImg(lineii):
                result_idx.append(ii)
                continue
            #--------Include and stop at any heading-----------
            if isheader:
                result_idx.append(ii)
                return result_idx

            #------------Check indent level change------------
            if sameblock and abs(tablvl-lvl)>1:
                sameblock=False
            #-----------Stop at a lower indent level-----------
            if tablvl-lvl>=1 and not sameblock:
                return result_idx

            tagsatline=self._tag_re.findall(lineii)

            #------Stil in the same tag def block, include and move on-----------
            if len(tagsatline)>0 and sameblock:
                result_idx.append(ii)
                continue

            #------Stop at another tag def line--------
            if len(tagsatline)>0 and not sameblock:
                return result_idx

            #-------Stop at indent level higher by 2------------
            if lvl-tablvl>=2:
                return result_idx

            #--Include lines at same or 1 higher indent level--
            if lvl-tablvl<=1 or lvl==0:
                result_idx.append(ii)

        return result_idx


    def searchDown(self,lines,tag,lineidx,lvl):
        result_idx=[]
        sameblock=True

        for ii in range(lineidx+1,len(lines)):
            lineii=lines[ii]
            tablvl=self.space2tab(lineii)[1]
            isheader=self.isHeader(lineii)

            if self.isEmpty(lineii):
                result_idx.append(ii)
                continue
            if self.isImg(lineii):
                result_idx.append(ii)
                continue
            if isheader:
                return result_idx

            if sameblock and abs(tablvl-lvl)>=1:
                sameblock=False

            #----------Stop at a higher indent level----------
            if lvl-tablvl>0:
                return result_idx

            tagsatline=self._tag_re.findall(lineii)

            #------Stil in the same tag def block, move on-----------
            if len(tagsatline)>0 and sameblock:
                continue

            #-------Include same or lower indent levels-------
            if tablvl>=lvl:
                result_idx.append(ii)

        return result_idx




    def findAllTags(self,lines):

        #----------------Loop through lines----------------
        tagdict={}
        for ll, tt in enumerate(lines):
            tt, tabnum=self.space2tab(tt)
            tagll=self._tag_re.findall(tt)

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
        text=text.encode('utf8')
        text = re.sub("\r\n|\r", "\n", text)
        lines=text.split('\n')
        lines=[ii+'\n' for ii in lines]

        #------------------Find all tags------------------
        tagdict=self.findAllTags(lines)

        #-------------Extract line idx by tag------------------
        result_idx=[]

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
        result_idx=set(result_idx)
        result_lines=[lines[ii] for ii in result_idx]
        result_lines=u''.join(result_lines)

        return result_lines





#-------------------Read in text file and store data-------------------
def readFile(abpath_in,verbose=True):
    '''Read in text file and store data

    <abpath_in>: str, absolute path to input txt.
    '''

    if not os.path.exists(abpath_in):
        raise Exception("\n# <tagextract>: Input file not found.")

    if verbose:
        print('\n# <tagextract>: Open input file:')
        print(abpath_in)
        print('\n# <tagextract>: Reading lines...')
        
    lines=[]

    with open(abpath_in, 'r') as fin:
        for line in fin:
            lines.append(line)
    lines=u''.join(lines)

    if verbose:
        print('# <tagextract>: Got all data.')

    return lines



#---------------Save result to file---------------
def saveFile(abpath_out,text,verbose=True):

    if os.path.isfile(abpath_out):
        os.remove(abpath_out)

    if verbose:
        print('\n# <tagextract>: Saving result to:')
        print(abpath_out)

    with open(abpath_out, mode='a') as fout:
        fout.write(text)

    return



#-------------------Extract tagged texts from file.-------------------
def main(filein,fileout,tag,syntax='markdown',verbose=True):
    '''Extract tagged texts from file.

    filein
    '''

    text=readFile(filein,verbose)
    if verbose:
        print('# <tagextract>: Extracting tagged lines...')
    tagfinder=TagFinder(syntax)
    newtext=tagfinder.extractTag(text,tag)

    headersym='# ' if syntax=='markdown' else '====='
    header='Summary of tag: %s' %tag
    header='%s %s %s' %(headersym, header, headersym)
    newtext=header+'\n\n'+newtext

    saveFile(fileout,newtext,verbose)

    return



#-----------------------Main-----------------------
if __name__=='__main__':

    parser=argparse.ArgumentParser(description=\
            'Extract text lines by tags')

    parser.add_argument('file',type=str,help='Input text file')
    parser.add_argument('tag',type=str,help='Tag to extract')
    parser.add_argument('-o','--out',type=str,\
            help='Optional output file name.')

    syntax=parser.add_mutually_exclusive_group(required=True)
    syntax.add_argument('-m','--markdown', action='store_true',\
            help='Input text uses markdown syntax.')
    syntax.add_argument('-z','--zim', action='store_true',\
            help='Input text uses zim wiki syntax.')

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

    if args.markdown:
        SYNTAX='markdown'
    elif args.zim:
        SYNTAX='zim'

    main(FILEIN,FILEOUT,TAG,SYNTAX,args.verbose)


