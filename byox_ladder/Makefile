# Regenerate the Build-Your-Own-X difficulty ladders.
#
#   make build   # fetch README -> parse -> build both standalone pages
#   make clean   # remove the fetched README copy and derived data

README_URL = https://raw.githubusercontent.com/codecrafters-io/build-your-own-x/master/README.md

.PHONY: build clean

build: guides.json
	python3 build_pages.py

guides.json: byox-readme.md parse_guides.py
	python3 parse_guides.py

byox-readme.md:
	curl -fsSL "$(README_URL)" -o byox-readme.md

clean:
	rm -f byox-readme.md guides.json
