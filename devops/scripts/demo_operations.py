"""Temporarily enable the local synthetic importer, then disable it on exit."""
import os
import sys
import manage

if __name__ == '__main__':
    try:
        os.environ['SUPERSPORTS_SYNTHETIC_IMPORT_ENABLED'] = 'true'
        manage.compose(['up','-d','--build','--no-deps','--wait','--wait-timeout','120','orders'])
        manage.run([str(manage.ROOT/'.venv/bin/python'), str(manage.ROOT/'data/pipelines/demo-commerce/import.py'), *sys.argv[1:]])
    finally:
        os.environ['SUPERSPORTS_SYNTHETIC_IMPORT_ENABLED'] = 'false'
        manage.compose(['up','-d','--no-deps','--wait','--wait-timeout','120','orders'])
