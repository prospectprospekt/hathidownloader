from bs4 import BeautifulSoup
import requests
import os
from math import ceil, floor
import subprocess
from re import search
import argparse
# functions below have to be executed in the directory where the images are going to be downloaded
# gets upright and upside down image for merging
def get_two_images(full_text_id, page_num): 
  url_upright = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=full;format=image/png"
  while True:
    response = requests.get(url_upright)
    if response.status_code == 200:
      # save height for later
      height = search(r"\d*$", response.headers['x-image-size'])
      image_path = f"{page_num}_upright.png"
      with open(image_path, 'wb') as file:
        file.write(response.content)
      break
    print(f"Page {page_num}: got status code {response.status_code} while trying to get upright image. Trying again.")
  url_upside_down = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=full;format=image/png;rotation=180"
  while True:
    response = requests.get(url_upside_down)
    if response.status_code == 200:
      image_path = f"{page_num}_upside_down.png"
      with open(image_path, 'wb') as file:
        file.write(response.content)
      break
    print(f"Page {page_num}: got status code {response.status_code} while trying to get upside down image. Trying again.")
  # return height for use in the merge_images function
  return int(height.group()) 
# requires: cd to directory where images are going to be downloaded
# and imagemagick
# modifies: command line? and print
# effects: joins image for page number using imagemagick
def merge_images(full_text_id, page_num, height):
  half = height / 2.0
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
# function to call when downloading a single image
def get_single_image(full_text_id, page_num):
  # do not do anything if image already exists
  upright_image_name = f"{page_num}_upright.png"
  upside_down_image_name = f"{page_num}_upside_down.png"
  cropped_upright = f"Cropped_{page_num}_upright.png"
  cropped_upside_down = f"Cropped_{page_num}_upside_down.png"
  cropped_upside_down_rotated = f"Rotated_cropped_{page_num}_upside_down.png"
  error_message = f"Page {page_num}: file already exists, not downloading image!"
  if os.path.exists(upright_image_name):
    print(error_message)
    return None
  elif os.path.exists(upside_down_image_name):
    print(error_message)
    return None
  elif os.path.exists(cropped_upright):
    print(error_message)
    return None
  elif os.path.exists(cropped_upside_down):
    print(error_message)
    return None
  elif os.path.exists(cropped_upside_down_rotated):
    print(error_message)
    return None
  # finds the height while downloading the two images
  height = get_two_images(full_text_id, page_num)
  merge_images(full_text_id, page_num, height)
  # delete leftover images
  os.remove(upright_image_name)
  os.remove(upside_down_image_name)
  os.remove(cropped_upright)
  os.remove(cropped_upside_down)
  os.remove(cropped_upside_down_rotated)
  print(f"Page {page_num}: sucessfully assembled png image!")
  return None
def convert_image(full_text_id, page_num):
  # get the smallest files to determine bitonality/color
  page_url_for_determining_bitonality = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=1"
  page_url_for_determining_color = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=1;format=image/"
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
      # bitonal files are double the width/height of non-bitonal files
      else:
        # hash of converted djvu file is the same whether the image is
        # converted to pbm or pgm; using pbm because djvulibre documentation
        # says so
        pnm_name = f"{page_num}.pbm" 
        imagemagick_command = ["magick", f"{page_num}.png", pnm_name]
        djvulibre_command = ["cjb2", "-dpi", "200", pnm_name, f"{page_num}.djvu"]
        break
    print(f"Page {page_num}: got status code {response_for_bitonality.status_code} while trying to determine bitonality! Trying again...")
  subprocess.run(imagemagick_command)
  subprocess.run(djvulibre_command)
  return None
# deletes pnm file after converting it to djvu
def convert_image_to_djvu(full_text_id, page_num):
  pgm = f"{page_num}.pgm" 
  pbm = f"{page_num}.pbm"
  ppm = f"{page_num}.ppm"
  # do not move on if pnm file already exists
  if os.path.exists(pgm) or os.path.exists(pbm) or os.path.exists(ppm):
    print(f"Page {page_num}: pnm files already exist, not conveting to djvu!")
    return None
  convert_image(full_text_id, page_num)
  if os.path.exists(pgm):
    os.remove(pgm)
    print(f"Page {page_num}: pgm file successfully deleted!")
  elif os.path.exists(pbm):
    os.remove(pbm)
    print(f"Page {page_num}: pbm file successfully deleted!")
  elif os.path.exists(ppm):
    os.remove(ppm)
    print(f"Page {page_num}: ppm file successfully deleted!")
  print(f"Page {page_num}: sucessfully converted to djvu!")
  return None
def generate_blank_djvu(full_text_id, page_num):
  print(f"Page {page_num}: getting blank djvu")
  # get the height and width, and image type
  url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={full_text_id};seq={page_num};size=full"
  while True:
    response = requests.get(url)
    if response.status_code == 200:
      width = search(r"^\d*", response.headers['x-image-size'])
      height = search(r"\d*$", response.headers['x-image-size'])
      content_type = response.headers['content-type']
      if content_type == "image/png":
        subprocess.run(["magick", "-size", f"{width.group()}x{height.group()}", "canvas:white", f"{page_num}.pbm"])
        subprocess.run(["cjb2", "-dpi", "200", f"{page_num}.pbm", f"{page_num}.djvu"])
      else:
        # non-bitonal images are half the width and height of bitonal images
        subprocess.run(["magick", "-size", f"{width.group()}x{height.group()}", "canvas:white", f"{page_num}.pbm"])
        subprocess.run(["cjb2", "-dpi", "100", f"{page_num}.pbm", f"{page_num}.djvu"])
      break   
    print(f"Page {page_num}: got status code {response.status_code}. Trying again")
  print(f"Page {page_num}:blank djvu sucessfully created!")
  return None
# this is copied from quicktranscribe. Code from here should be executed 
# without going into the directory where the images will be
# downloaded
# https://github.com/PseudoSkull/QuickTranscribe/blob/main/hathi.py
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
def download_hathi_images(full_text_id, total_page_num):
  # _images is appended to directory name so that you can upload them
  # to the internet archive to generate ocr
  directory_name = f"{full_text_id}_images"
  # make directory if it doesn't exist
  if not os.path.exists(directory_name):
    os.mkdir(directory_name)
  # cd to the directory
  prevdir = os.getcwd()
  os.chdir(directory_name)
  for i in range(total_page_num):
    page_num = i + 1
    # do not download image if image already exists
    if os.path.exists(f"{page_num}.png"):
      print(f"Page {page_num}: image already exists!")
      continue
    get_single_image(full_text_id, page_num)
  print(f"All images downloaded!")
  # exit the directory
  os.chdir(prevdir)
  return None
def convert_hathi_images(full_text_id, total_page_num):
  directory_name = f"{full_text_id}_images"
  if not os.path.exists(directory_name):
    print(f"Directory named {full_text_id}_images doesn't exist!")
    return None
  prevdir = os.getcwd()
  os.chdir(directory_name)
  djvm_command = ["djvm", "-c", "final.djvu"]
  for i in range(total_page_num + 1):
    page_num = i + 1
    # account for purposefully deleted pages
    if not os.path.exists(f"{page_num}.png"):
      continue
    djvm_command.append(f"{page_num}.djvu")
    if not os.path.exists(f"{page_num}.djvu"):
      convert_image_to_djvu(full_text_id, page_num)
  print("All images converted to djvu. Combining...")
  subprocess.run(djvm_command)
  print(f"Combined! the final djvu file can be found as final.djvu in the same directory where the images are")
  os.chdir(prevdir)
  return None
parser = argparse.ArgumentParser()
parser.add_argument("-id", help="id for page")
parser.add_argument("-p", help="page number")
parser.add_argument("-dsi", action="store_true", help="download single page")
parser.add_argument("-dap", action="store_true", help="download all pages")
parser.add_argument("-cap", action="store_true", help="convert all already=downloaded images")
args = parser.parse_args()
if args.dsi == 1:
  get_single_image(args.id, args.p)
elif args.dap == 1:
  pages = get_number_of_pages(args.id)
  download_hathi_images(args.id, pages)
elif args.cap == 1:
  pages = get_number_of_pages(args.id)
  convert_hathi_images(args.id, pages)
# assume that user wants to both download and convert images
else:
  pages = get_number_of_pages(args.id)
  download_hathi_images(args.id, pages)
  convert_hathi_images(args.id, pages)
