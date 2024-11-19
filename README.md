# hathi2djvu

This downloads HathiTrust images without the watermark and converts them to a singular DjVu file. Parts of this (the page number finder) are copied from SnowyCinema's QuickTranscribe

## Prerequisites
To use this program, you will need:
* Python
* ImageMagick
* BeautifulSoup (https://www.crummy.com/software/BeautifulSoup/)
* and the requests module (https://requests.readthedocs.io/en/latest/user/install/#install)
## How to use 
The simplest use is the command python hathi2djvu.py -id [hathitrust id], which will download the images and convert them to djvu. You can also download a single png image with "python hathi2djvu.py -id [hathitrust id] -p [page number] -dsp. python hathi2djvu.py -id [hathitrust id] -dap downloads all the pages without converting for ocr/page editing and removal purposes, and python hathi2djvu.py -id [hathitrust id] -cap converts an existing directory of images (that has to be title "[hathitrust_id]_images"). 

-dsp stands for "download single page", -dap stands for "download all pages", and -cap stands for "convert all pages"

## How to add ocr 
This program is not able to add ocr to the djvu files that it creates. For that you can compress the directory the images are downloaded in and upload the resultant zip file to the Internet Archive, which will create a djvu.xml which can be combined with the djvu file. I might be wrong on this though, as I have never tried this method. 



