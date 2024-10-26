from bs4 import BeautifulSoup
import requests
from contextlib import chdir
import os
from math import ceil, floor
import subprocess
import argparse
# functions below have to be executed in the directory where the images are going to be downloaded
# gets upright and upside down image for merging
def get_two_images(full_text_id, page_num, orientation):
  if orientation:  
    url_upright = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=full;format=image/png"
    while True:
      response = requests.get(url_upright)
      if response.status_code == 200:
        image_path = f"{page_num}_upright.png"
        with open(image_path, 'wb') as file:
          file.write(response.content)
        break
      print(f"Page {page_num}: got status code {response.status_code} while trying to get upright image. Trying again.")
  else:
    url_upside_down = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=full;format=image/png;rotation=180"
    while True:
      response = requests.get(url_upside_down)
      if response.status_code == 200:
        image_path = f"{page_num}_upside_down.png"
        with open(image_path, 'wb') as file:
          file.write(response.content)
        break
      print(f"Page {page_num}: got status code {response.status_code} while trying to get upside down image. Trying again.")
  return None
# finds the height of the image via requests
# modifies: print
def find_height(full_text_id, page_num):
  url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=full;format=image/png"
  while True:
    response = requests.get(url)
    if response.status_code == 200:
      # get last four characters of x-image-size, which is the height
      size = response.headers['x-image-size']
      break
    print(f"Page {page_num}: didn't get height with status code {response.status_code}. Trying again.")
  return int(size[-4:])
# requires: cd to directory where images are going to be downloaded
# and imagemagick
# modifies: command line? and print
# effects: joins image for page number using imagemagick
def merge_images(full_text_id, page_num):
  half = find_height(full_text_id, page_num) / 2.0
  larger_half = int(ceil(half))
  smaller_half = int(floor(half))
  upright_image_name = f"{page_num}_upright.png"
  upside_down_image_name = f"{page_num}_upside_down.png"
  cropped_upright = f"Cropped_{page_num}_upright.png"
  cropped_upside_down = f"Cropped_{page_num}_upside_down.png"
  cropped_upside_down_rotated = f"Rotated_cropped_{page_num}_upside_down.png"
  final_image = f"{page_num}.png"
  upper_image_crop_command = ["magick", upright_image_name, "-gravity", "South", "-chop", f"0x{larger_half}", cropped_upright]
  upside_down_image_crop_command = ["magick", upside_down_image_name, "-gravity", "South", "-chop", f"0x{smaller_half}", cropped_upside_down]
  rotate_upside_down_command = ["magick", cropped_upside_down, "-rotate", "-180", cropped_upside_down_rotated]
  join = ["magick", cropped_upright, cropped_upside_down_rotated, "-append", final_image]
  subprocess.run(upper_image_crop_command)
  subprocess.run(upside_down_image_crop_command)
  subprocess.run(rotate_upside_down_command)
  subprocess.run(join)
  return None
# delete files left over from merging top and bottom images
def delete_files_for_single_image(page_num):
  upright_image_name = f"{page_num}_upright.png"
  upside_down_image_name = f"{page_num}_upside_down.png"
  cropped_upright = f"Cropped_{page_num}_upright.png"
  cropped_upside_down = f"Cropped_{page_num}_upside_down.png"
  cropped_upside_down_rotated = f"Rotated_cropped_{page_num}_upside_down.png"
  os.remove(upright_image_name)
  os.remove(upside_down_image_name)
  os.remove(cropped_upright)
  os.remove(cropped_upside_down)
  os.remove(cropped_upside_down_rotated)
  print(f"Page {page_num}: {page_num}_upright.png, {page_num}_upside_down.png, Cropped_{page_num}_upright.png, Cropped_{page_num}_upside_down.png, and Rotated_cropped_{page_num}_upside_down.png successfully deleted!")
  return None
# function to call when downloading a single image
def get_single_image(full_text_id, page_num):
  get_two_images(full_text_id, page_num, True)
  get_two_images(full_text_id, page_num, False)
  merge_images(full_text_id, page_num)
  delete_files_for_single_image(page_num)
  print(f"Page {page_num}: sucessfully assembled png image!")
  return None
# return array for the subprocess
def convert_image(full_text_id, page_num):
  page_url_for_determining_bitonality = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=1000"
  page_url_for_determining_color = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=1000;format=image/"
  # if image is jpeg, then it is either greyscale or color. If it is png then it is bitonal
  while True:
    response_for_bitonality = requests.get(page_url_for_determining_bitonality)
    if response_for_bitonality.status_code == 200:
      content_type = response_for_bitonality.headers['content-type']
      if content_type == "image/jpeg":
        # determine if it is greyscale or color if image is not bitonal
        # via first line of ppm file
        while True:
          response_for_color = requests.get(page_url_for_determining_color)
          # the default dpi (100) is used because that's what 
          # ia_upload uses and what is recommended by djvulibre
          if response_for_color.status_code == 200:
            # get first line with requests
            first_line = response_for_color.text.partition("\n")[0]
            # p5 means that file is pgm, or that the page is greyscale
            if first_line == "P5":
              pnm_name = f"{page_num}.pgm"
              imagemagick_command = ["magick", f"{page_num}.png", pnm_name]
              djvulibre_command = ["c44", pnm_name, f"{page_num}.djvu"]
            # this means that the first line is P6, or the file is ppm
            # or in color
            else:
              pnm_name = f"{page_num}.ppm"
              imagemagick_command = ["magick", f"{page_num}.png", pnm_name]
              djvulibre_command = ["c44", pnm_name, f"{page_num}.djvu"]
            break
          print(f"Page {page_num}: got status code {response_for_color.status_code} while trying to determine color/greyscale, trying again.")
        break
      # if image is bitonal, convert with cjb2 w/ dpi 200 because
      # bitonal files are double the size of non-bitonal files
      else:
        pnm_name = f"{page_num}.pbm"
        imagemagick_command = ["magick", f"{page_num}.png", pnm_name]
        djvulibre_command = ["cjb2", "-dpi", "200", pnm_name, f"{page_num}.djvu"]
        break
    print(f"Page {page_num}: got status code {response_for_bitonality.status_code} while trying to determine bitonality! Trying again...")
  subprocess.run(imagemagick_command)
  subprocess.run(djvulibre_command)
  return None
# deletes pnm file after converting it to djvu
def delete_pnm_file(page_num):
  pgm = f"{page_num}.pgm" 
  pbm = f"{page_num}.pbm"
  ppm = f"{page_num}.ppm"
  if os.path.exists(pgm):
    os.remove(pgm)
    print(f"Page {page_num}: pgm file successfully deleted!")
  elif os.path.exists(pbm):
    os.remove(pbm)
    print(f"Page {page_num}: pbm file successfully deleted!")
  elif os.path.exists(ppm):
    os.remove(ppm)
    print(f"Page {page_num}: ppm file successfully deleted!")
  return None
def convert_image_to_djvu(full_text_id, page_num):
  convert_image(full_text_id, page_num)
  delete_pnm_file(page_num)
  print(f"Page {page_num}: sucessfully converted to djvu!")
  return None      
# this is copied from quicktranscribe
# https://github.com/PseudoSkull/QuickTranscribe/blob/main/hathi.py
# starting from here, the functions do not get executed in the same directory that the images are downloaded in
def get_number_of_pages(full_text_id):
  print("Retrieving number of pages in scan...")
  url = f"https://babel.hathitrust.org/cgi/pt?id={full_text_id}"
  response = requests.get(url)
  if response.status_code == 200:
    print("Response code 200. Parsing the HTML...")
    soup = BeautifulSoup(response.content, 'html.parser')
    output_group = soup.find('div', class_='bg-dark')
    script_tag = soup.find('script')
    # Get the JavaScript code within the script tag
    js_code = script_tag.string
    # Now, extract the value of "HT.params.totalSeq" from the JavaScript code
    total_seq_value = None
    lines = js_code.splitlines()
    for line in lines:
      if 'HT.params.totalSeq' in line:
        total_seq_value = line.split('=')[-1].strip().rstrip(';')
        break
    number_of_pages = int(total_seq_value)
    print(f"Number of pages found! Number of pages in scan: {number_of_pages}")
    return number_of_pages
  print(f"Response code not 200. Was: {response.status_code}")
  return None
# temporary measure, will make more complicated later
parser = argparse.ArgumentParser()
parser.add_argument('-id')
args = parser.parse_args()
pages = get_number_of_pages(args.id)
print(f"Making directory for HathiTrust book with id get_number_of_pages{args.id}")
directory = f"{args.id}_images_and_djvu_files"
try:
  os.mkdir(directory)
except: 
  print("Directory already made")
# go to the directory where the hathitrust images will download
cwd = os.getcwd()
os.chdir(f"{cwd}/{directory}")
finalcommand = ["djvm", "-c"]
for i in range(pages):
  finalcommand.append(f"{i}.djvu")
  if os.path.isfile(f"{i}.djvu"):
    print(f"skipping page {i} because djvu file already exists")
    continue
  if os.path.isfile(f"{i}.png"):
    convert_image_to_djvu(args.id, i)
    print(f"skipping page {i} because png file already exists")
  get_single_image(args.id, i)
  convert_image_to_djvu(args.id, i)
  print(f"page {i} successfully downloaded and converted")
finalcommand.append(f"{args.id}.djvu")
print(f"running final command")
subprocess.run(finalcommand)
os.chdir(cwd)

