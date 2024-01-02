pip install -r requirements.txt
pip install --upgrade --pre --extra-index-url https://marcelotduarte.github.io/packages/ cx_Freeze
cxfreeze -O -c starmap.py --include-files ./assets/ --target-dir dist