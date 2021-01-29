import sys
import requests
import zipfile
import os
from pathlib import Path, PurePath
import shutil
from collections import defaultdict
import numpy as np
import pandas as pd
import re
import plotly.express as px

def downloadPGN(lastname, directory_to_extract_to = 'downloads'):
    """
    The function downloads the PGN file for further processing to the ../downloads folder.

    Input:
    lastname(str): last name of the player

    Output:
    None, downloads and unpacks zip archive with a pgn file
    """

    lastname = lastname.lower()[0].upper() + lastname.lower()[1:]
    try:
        print('Downloading ZIP with PGNs of ' + lastname)
        zipFileUrl = "https://www.pgnmentor.com/players/" + lastname + ".zip"
        zipFile = requests.get(zipFileUrl)
        print("Download successful")
    except:
        print("ERROR: downlading was not succesful")
        return None
    #Checking if ../downloads folder exists and creates empty one
    if not os.path.exists(directory_to_extract_to):
        os.makedirs(directory_to_extract_to)
    else:
        shutil.rmtree(directory_to_extract_to) #Removes all the subdirectories!
        os.makedirs(directory_to_extract_to)
    try:
        path_to_zip_file = directory_to_extract_to + "/" + lastname + '.zip'
        #Saving zip file
        with open(os.fspath(PurePath(path_to_zip_file)), 'wb') as f:
            f.write(zipFile.content)
        print("Saving zip successful")
    except:
        print("ERROR: saving zip was not successful")
        return None
    try:
        #Unpacking zip file
        zip_ref = zipfile.ZipFile(os.fspath(PurePath(path_to_zip_file)), 'r')
        zip_ref.extractall(os.fspath(PurePath(directory_to_extract_to)))
        zip_ref.close()

        print("Unpacked successfully")
    except:
        print("ERROR: unpackng of zip was not successful. Probably the player was not found")
        return None

def convertPGNtoDF(path):
    """
    The function converts the PGN file to the Data Frame for further processing.

    Input:
    path(str): path to the PGN file

    Output:
    pandas DataFrame

    """
    with open(path, 'r', encoding='cp1252') as file:
        data_from_pgn = file.read()

    dct = defaultdict(list)

    moves = False
    for element in data_from_pgn.split("\n\n"):
        tags=['Event', 'Site', 'Date', 'Round', 'White', 'Black', 'Result', 'WhiteElo', 'BlackElo', 'ECO']
        if moves:
            dct["Moves"].append(element)
            moves = False

        else:
            for t in re.findall("\[.*\]", element):
                tag = t[1:-1].split('"')[0][:-1]
                val = t[1:-1].split('"')[1]
                dct[tag].append(val)
                tags.remove(tag)

            for t in tags:
                dct[t].append(np.nan)
                #print("nan for ", tag)
            moves = True
    maxLen = 0
    cat = ""
    for d in dct:
        #print(d,":",len(dct[d]))
        if len(dct[d])>=maxLen:
            maxLen=len(dct[d])
    for d in dct:
        if len(dct[d])<maxLen:
            dct[d].append([np.nan]*(maxLen-len(dct[d])))
    return pd.DataFrame(dct)

def getEcoDescription(eco, ecoUrl = 'https://www.chessgames.com/chessecohelp.html'):
    """
    The function returns a description of an opening based on its ECO code

    Input:
    eco (str): ECO code, e.g. 'A08'
    ecoUrl(str): source of the table with descriptions,
                 default: 'https://www.chessgames.com/chessecohelp.html'

    Output (str): string with a description or 'Description was not found' in case of abscence
    """

    pathToEco = './downloads/eco.pkl'
    if os.path.isfile(pathToEco):
        ecoDf = pd.read_pickle(pathToEco)
    else:
        ecoDf = pd.read_html(ecoUrl)[0]
        ecoDf.to_pickle(pathToEco)
    try:
        result = ecoDf[ecoDf[0]==eco].iloc[0][1]
    except:
        result = 'Description was not found'
    return result

def resultToString(result, white):
    """
    The function returns if the game was won based on result and color of figures
    Input:
    result(str): result in format '1-0','1/2-1/2', '0-1'
    white(bool): True if white, False if black

    Output:
    str: result of a game: 'won', 'lost', 'tie' or 'unknown'
    """
    wonSet = {('1', True),
              ('0', False)}
    tieSet = {('1/2', True),
              ('1/2', False)}
    lostSet = {('1', False),
               ('0', True)}

    if (result.split("-")[0], white) in wonSet:
        return 'won'
    elif (result.split("-")[0], white) in tieSet:
        return 'tie'
    elif (result.split("-")[0], white) in lostSet:
        return 'lost'
    else:
        return 'unknown'

def getTopOpenings(lastname, top=30, fltr='all'):
    """
    The function returns a pandas datframe with ECO codes and number of appearances of top openings.
    The function also creates a barchart in HTML format in the outputs directory.

    Input:
    lastname(str): player's lastname
    top(int):   number of top openings, default: 30
    fltr(str):  'all': take into all games,
                'won': take into account only won games,
                'lost': take into account only lost games,
                'tie': take into account only tie games,
                default: 'all'

    Outputs:
    pandas data frame with columns ECO and Frequency (number of appearances of top openings)

    """
    #Need conversion because of sys.arg string nature
    top = int(top)
    lastname = lastname.lower()[0].upper() + lastname.lower()[1:]
    directory_to_extract_to='outputs'
    pathToRawDf = directory_to_extract_to+f'/{lastname}RawDf.pkl'

    #Checking if the dataframe for the player was already formed for not downloading again
    if os.path.isfile(pathToRawDf):
        rawDf=pd.read_pickle(pathToRawDf)
        print('Dataframe exists. Reading.')
    else:
        print('Dataframe does not exist. Proceeding to download.')
         #Checking if ../outputs folder exists and creates empty one
        if not os.path.exists(directory_to_extract_to):
            os.makedirs(directory_to_extract_to)
        else:
            shutil.rmtree(directory_to_extract_to) #Removes all the subdirectories!
            os.makedirs(directory_to_extract_to)

        try:
            downloadPGN(lastname)
        except:
            return None

        path_to_pgn = "".join(('downloads/',lastname,'.pgn'))

        try:
            rawDf = convertPGNtoDF(path_to_pgn)
        except:
            return None

        rawDf["Won"]=rawDf.apply(lambda x: resultToString(x['Result'], x['White'].split(",")[0]==lastname), axis=1)
        rawDf.to_pickle(pathToRawDf)

    if fltr!='all':
        df = rawDf[rawDf['Won']==fltr].groupby("ECO").count().sort_values(by="Event", ascending=False).head(top)
    else:
        df = rawDf.groupby("ECO").count().sort_values(by="Event", ascending=False).head(top)

    df.reset_index(inplace=True)
    df.drop(df.iloc[:, 2:], axis = 1, inplace = True)
    df.columns=["ECO","Frequency"]
    df["Description"]=df["ECO"].map(getEcoDescription)
    df["Percentage"]=df["Frequency"]/len(rawDf)
    df["Percentage"]=df["Percentage"].apply(lambda x: round(x,4))


    fig = px.bar(df, x='ECO', y='Frequency',
             hover_data=['Description','Percentage'],
             height=400,
             title = "Top-"+str(top)+" openings of "+lastname+f" ({fltr})",
             labels={'ECO':'ECO (opening code)',
                     'Frequency':f'Frequency (of {len(rawDf)} games)',
                    'perc':'Ratio'},
             color='Frequency',
             color_continuous_scale="rdbu_r"
            )
    #fig.show()


    fig.write_html(directory_to_extract_to+f"/graph.html")
    print('Chart html saved succesfully')

    return df,rawDf

# class player():
#     def __init__(self, lastname):
#         self.lastname = lastname
#         self.df = getTopOpenings(self.lastname)[1]
#
#     def top(self, top=30, fltr='all'):
#         return getTopOpenings(self.lastname, top=30, fltr='all')[0]
#
#     def stats(self):
#         return self.df.groupby(by='Won').count()



def main():
    getTopOpenings(*sys.argv[1:])


if __name__ == '__main__':
    main()
