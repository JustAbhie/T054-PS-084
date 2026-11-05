import argparse
from pathlib import Path
from src.processor import process

def main():
    ap=argparse.ArgumentParser(description='T054 PS-084 procurement workflow engine')
    ap.add_argument('--data',default='data',help='Folder containing input CSV files and commands.txt')
    ap.add_argument('--out',default='outputs',help='Output folder for evaluation CSVs')
    args=ap.parse_args()
    p=process(args.data,args.out)
    print('PS-084 processing complete')
    for name,rows in p.rows.items(): print(f'{name}: {len(rows)} rows')
    print(f'Processing errors: {len(p.errors)}')
    for e in p.errors[:25]: print(' -',e)
    print('Output folder:',Path(args.out).resolve())
if __name__=='__main__':main()
