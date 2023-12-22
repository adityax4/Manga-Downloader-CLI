import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import threading
from PIL import Image
from fpdf import FPDF
from PyPDF2 import PdfMerger
import shutil
import time

DIR = os.getcwd()

# returns a list of images in a chapter
def page_links(url)->list:
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    div = str(soup.find("div", {"class": "container-chapter-reader"}))
    imgs = BeautifulSoup(div, 'html.parser').find_all("img")
    page_urls = []
    for i in imgs:
        page_urls.append(i['src'])
    return page_urls

# Downloads a list of images using multithreading.
def download_all_images(urls):
    def download(name,url):
        domain = urllib.parse.urlparse(url).netloc
        HEADERS = {
            'Accept': 'image/png,image/svg+xml,image/*;q=0.8,video/*;q=0.8,*/*;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.9999.999 Safari/537.36',
            'Host': domain, 'Accept-Language': 'en-ca', 'Referer': 'https://manganelo.com/',
            'Connection': 'keep-alive'
        }
        r = requests.get(url,headers=HEADERS, stream=True)
        with open(name, 'wb') as f:
            f.write(r.content)
        inputimage = Image.open(name).convert("RGBA")
        image = Image.new("RGB", inputimage.size, "WHITE")
        image.paste(inputimage, (0, 0), inputimage)
        os.remove(name)
        image.save(name)

    threads = []
    for i in range(len(urls)):
        t = threading.Thread(target=download, args=(str(i+1)+".jpg",urls[i]))
        threads.append(t)
        t.start()
    for thread in threads:
        thread.join()


def convert_to_pdf(name, imgs, pdfs, path):
    i = 0 
    for img in imgs:
        with Image.open(img).convert("RGBA") as inputimage:
            width, height = inputimage.size
            width, height = float(width * 0.264583), float(height * 0.264583)
            pdf = FPDF('P', 'mm', (width, height))
            pdf.add_page()
            pdf.image(img, 0, 0, width, height)
            pdf.output(pdfs[i], "F")

        os.remove(img)
        i += 1
        
    time.sleep(1)

    merger = PdfMerger()
    for pdf in pdfs:
        merger.append(pdf)
    merger.write(name + ".pdf")
    merger.close()
    os.rename(os.path.join(path, name + ".pdf"), os.path.join(DIR, name + ".pdf"))
    os.chdir(DIR)
    shutil.rmtree(path)
    print("Downloaded " + name + " successfully")



# Download chapter
def download_manga(name, url, chapters=None):
    print("Downloading " + str(name) + " from " + str(url))
    pages = page_links(url)
    num = len(pages)
    print("Downloading " + str(num) + " pages")
    
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    
    path = os.path.join(DIR, name)
    if not os.path.exists(path):
        os.mkdir(path)
    os.chdir(path)
    download_all_images(pages)
    imgs = [str(i+1)+".jpg" for i in range(num)]
    pdfs = [str(i+1)+".pdf" for i in range(num)]
    convert_to_pdf(name, imgs, pdfs, path)

    pass


# return a dictionary of chapter links (name->link)
def chapter_links(URL) -> dict:
    r = requests.get(URL)
    soup = BeautifulSoup(r.content, 'html.parser')
    chapters = soup.find_all("a", {"class": "chapter-name text-nowrap"})
    links = {}
    for chapter in chapters:
        links[chapter.text] = chapter['href']
    return links


def main():
    URL = input("Enter the URL of the manga: ")
    print("URL: " + URL)
    chapters = chapter_links(URL)
    
    # Display available chapters for selection in ascending order based on chapter numbers
    for index, chapter in enumerate(sorted(chapters, key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else float('inf')), start=1):
        print(f"{index}. {chapter}")

    total_chapters = len(chapters)
    
    while True:
        selection = input(f"Enter the chapters to download (e.g., '1-10', '5', '1,3,5'): ")

        selected_chapters = []
        if '-' in selection:
            start, end = map(int, selection.split('-'))
            selected_chapters = sorted(chapters, key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else float('inf'))[start - 1:end]
        elif ',' in selection:
            chapters_list = list(map(int, selection.split(',')))
            selected_chapters = [sorted(chapters, key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else float('inf'))[num - 1] for num in chapters_list]
        else:
            chapter_number = int(selection)
            if 1 <= chapter_number <= total_chapters:
                selected_chapters.append(sorted(chapters, key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else float('inf'))[chapter_number - 1])
            else:
                print(f"Invalid chapter number. Please enter a number between 1 and {total_chapters}.")
                continue

        for chapter in selected_chapters:
            download_manga(chapter, chapters[chapter])

        download_more = input("Do you want to download more chapters? (yes/no): ")
        if download_more.lower() != 'yes':
            break

main()