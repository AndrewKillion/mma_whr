import pandas as pd 

data = pd.read_parquet('data/local/ufc_fights.parquet')


if __name__ == 'main':
    print(data)
    