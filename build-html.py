import os
import markdown
from markdown.extensions.toc import TocExtension

baseFolder = os.getcwd()
readmePath = os.path.join(baseFolder, 'README.md')
extensionPath = os.path.join(baseFolder, 'ScaleFast.roboFontExt')

# -------------
# generate html
# -------------

htmlFolder = os.path.join(extensionPath, 'html')
htmlPath = os.path.join(htmlFolder, 'index.html')

htmlTemplate = '''\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ScaleFast</title>
<link rel="stylesheet" href="github-markdown.css">
<style>
  html {
    margin-left: auto;
    margin-right: auto;
  }
  .headerlink {
    opacity: 0.0;
  }
  body h1:hover a.headerlink,
  body h2:hover a.headerlink,
  body h3:hover a.headerlink,
  body h4:hover a.headerlink {
    opacity: 1.0;
  }
</style>
</head>
<body>
%s
</body>
</html>
'''

with open(readmePath, mode="r", encoding="utf-8") as f:
    markdownSource = f.read()

M = markdown.Markdown(extensions=[TocExtension(permalink=True)])
html = htmlTemplate % M.convert(markdownSource)

with open(htmlPath, mode="w", encoding="utf-8") as htmlFile:
    htmlFile.write(html)

# -----------
# copy images
# -----------

import shutil

imgsFolder = os.path.join(baseFolder, 'images')
htmlImgsFolder = os.path.join(htmlFolder, 'images')

for f in os.listdir(imgsFolder):
    if not os.path.splitext(f)[-1] in ['.png', '.jpg', '.jpeg']:
        continue
    imgPath = os.path.join(imgsFolder, f)
    shutil.copy2(imgPath, htmlImgsFolder)
