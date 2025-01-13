#!/usr/bin/env python

import os
import glob
import subprocess
import re
import optparse


def main():

    parser = optparse.OptionParser(usage='Usage: %prog -i <source directory> <options> -o <output file>')
    parser.add_option('-i', dest='djvu', action='store',\
                             help='the source djvu file to perfrom OCR on')
    parser.add_option('-l', dest='lang', action='store', default='eng',\
                             help="OCR language (default: 'eng')" )
    parser.add_option('-d', dest='debug', action='store_true', default=False,\
                             help='enable debugging information' )
    parser.add_option('-t', dest='tess_out', action='store_true', default=False,\
                             help='enable tesseract output' )
    parser.add_option('-c', dest='clean', action='store_true', default=False,\
                             help='use textcleaner and imagemagick to convert the image to bitonal black and white' )
    parser.add_option('-o', dest='output', action='store',\
                             help='output a human readable text file to a given file path' )
    parser.add_option('-u', dest='update', action='store_true', default=False,\
                             help='update the djvu file text layer' )

    (opts, args) = parser.parse_args()

    # check mandatory options
    if opts.djvu is None:
        print("The input file '-i' must be given\n")
        parser.print_help()
        exit(-1)

    DjvuTesseract(opts)


class DjvuTesseract():

    def command(self, command, out=False, err=False):
        """Use subprocess.Popen" to run a command on the terminal and return the s result

        Required for python 2.6 since subprocess.check_output doesn't exist

        This function will trash output unless you explicitly ask it not to
        with quiet=False. This is so tesseract won't spam you with rubbish"""

        if out:
            std_out = subprocess.PIPE
        else:
            std_out = None

        if not err:
            std_err = subprocess.PIPE
        else:
            std_err = None


        proc = subprocess.Popen(command, stdout = std_out,  stderr=std_err)#std_out)
        out, err = proc.communicate()

        return out, err

    def complete(self):
        """Prints a "complete" message if debugging is on"""

        if self.opts.debug:
            print "complete"

    def calculate_djvu_length(self):

        cmd = ['djvused', self.opts.djvu, '-e', 'n']
        out, err = self.command(cmd, out=True)
        self.num_pages = int(out)

        if self.opts.debug:
            print "(INF) number of pages: %d" % self.num_pages

    def format_ocr_text(self, page):
        """Format a page's OCR'd text into a DJVU friendly form"""

        #read out of the text file that tesseract made
        ocr_text = open(self.ocr_text, 'r')

        # write into this file
        djvu_text = open( self.djvu_text, 'w' )

        text = "(page 0 0 1 1\n"

        self.out_text.write('\n## Page %d ###\n\n' % page )

        for line in ocr_text:

            #write to the human readable file
            self.out_text.write(line)

            # add each line of text
            # escaping " to \" as we go
            text += '(line 0 0 1 1 "%s")\n' % line.replace('\\', '\\\\').replace('"', '\\"').strip()

        text += ")\n"

        djvu_text.write( text )

        ocr_text.close()
        djvu_text.close()

    def process_pages(self):

        for page in range(1, self.num_pages+1): #djvu pages are 1-indexed

            if self.opts.debug:
                print "\n\t(INF) Processing page %d" % page

            if self.opts.debug:
                print "\t(INF) Extracting DjVu page to image . . .",
            # Extract page an image
            cmd = ['ddjvu', '-format=tiff', '-page=%d' % page, self.opts.djvu, self.temp_img]
            out, err = self.command(cmd)

            self.complete()

            #Cleanup image
            if self.opts.clean:
                if self.opts.debug:
                    print "\t(INF) Applying textcleaner . . .",

                # apply text cleaner
                cmd = ['./textcleaner', self.temp_img, self.temp_img]
                out, err = self.command(cmd)

                self.complete()

                if self.opts.debug:
                    print "\t(INF) Applying bitonal conversion . . .",

                # apply text cleaner
                cmd = ['convert', self.temp_img, '-threshold', '50%', self.temp_img]
                out, err = self.command(cmd)

                self.complete()

            if self.opts.debug:
                print "\t(INF) Beginning OCR. . .",

            # Perform OCR on the image
            cmd = ['tesseract', self.temp_img, self.temp_ocr, '-l', self.opts.lang]
            out, err = self.command(cmd, err=self.opts.tess_out)

            self.complete()

            # convert the OCR'd text to a DJVU friendly fomat and a human-friendly format
            self.format_ocr_text(page)

            # update the DJVU text layer
            if self.opts.update:

                if self.opts.debug:
                    print "\t(INF) Updating DJVU page . . .",

                # replace the text in the DJVU file
                cmd = ['djvused', self.opts.djvu, '-e', 'select %d; remove-txt' % page, "-s"]
                out, err = self.command(cmd)

                cmd = ['djvused', self.opts.djvu, '-e', 'select %d; set-txt %s'% (page, self.djvu_text), "-s"]
                out, err = self.command(cmd)

                self.complete()

    def process_djvu(self):

        if self.opts.debug:
            print "(INF) Processing %s" % self.opts.djvu

        # calculate DJVU length
        self.calculate_djvu_length()

        self.process_pages()


    def __init__(self, opts):
        self.opts = opts

        self.temp_img = "/tmp/TESSERACT-OCR-TEMP.tif"
        self.temp_ocr = "/tmp/TESSERACT-OCR-TEMP" #tesseract adds .txt

        self.ocr_text = self.temp_ocr + '.txt'

        # file to dump pase-wise formatted OCR'd text into
        self.djvu_text = "/tmp/TESSERACT-OCR-TEMP.djvu.txt"

        # file to dump human readable output into for the whole file
        if self.opts.output:
            output_filename = self.opts.output
        else: #dump in /tmp/
            output_filename = "/tmp/TESSERACT-OCR-TEMP.output.txt"

        self.out_text = open(output_filename, 'w')

        self.process_djvu()

if __name__ == "__main__":
    try:
        main()
    finally:
        None

"""
# note: structure which works
# print TXTDJVU "(page 0 0 1 1\n" ;
#   print TXTDJVU "     (line 0 0 1 1 \"toto\")\n" ;
#   print TXTDJVU "     (line 0 0 1 1 \"toto la la\")\n";
#   print TXTDJVU ")\n" ;
"""
