# This is the script, that gonna generate learn-cont/00-learn-cont.md file.
# Run it if you rename/add/delete files to the learn-cont folder

import os

from typing import List

DIR = "learn-cont"
MAIN_FILE = "00-learn-cont.md"
PREFIX = \
"""# Learn cont
This is the place to learn cont. Also, you could go look at some example code in `tests`, `examples` or
`std` folders.

Don't be afraid of asking questions in the issues tab or dming me on Discord,
I have the same username on Discord as on Github. 

# Table of contents
"""

articles: List[str] = os.listdir(DIR)
articles.remove(MAIN_FILE)
articles.sort()

table_of_contents = ""

for article in articles:
    prefix_index = article.find("-")
    if prefix_index == -1:  # there is no dash in the file name
        print(
            "Every file in the learn-cont directory must be of such format: 01-quick-start.md"
        )
        exit(1)

    suffix_index = article.find(".")
    if suffix_index == -1:  # there is no dot in the file name
        print(
            "Every file in the learn-cont directory must be of such format: 01-quick-start.md"
        )
        exit(1)

    words = article[prefix_index + 1:suffix_index].split("-")
    name = " ".join([word.capitalize() for word in words])

    table_of_contents += (
        f"* [{name}](https://github.com/farkon00/cont/blob/master/{DIR}/{article})\n"
    )
    with open(f"{DIR}/{article}", "r") as f:
        sections = filter(lambda x: x.startswith("## "), f.readlines())
    for title in sections:
        title = title.removeprefix("## ").removesuffix("\n")
        anchor = "-".join(title.lower().split())
        table_of_contents += (
            f"  * [{title}](https://github.com/farkon00/cont/blob/master/{DIR}/{article}#{anchor})\n"
        )

with open(f"{DIR}/{MAIN_FILE}", "w") as f:
    f.write(PREFIX + table_of_contents)
