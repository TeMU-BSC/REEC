#!/usr/bin/env python
# Imports
import reecapi.getters as reec
import json
import pymongo
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
import sys, os
from io import open
import argparse
from datetime import datetime

# Define constants
MODE_DATA = "data"
MODE_MONGO = "mongo"

# Function to process original reec records to the final shape.
def process_batch_reec_records(list_reec):
    lista_dicts = [None] * len(list_reec)
    # Iterate over the ids
    for i, count in zip(list_reec,range(len(list_reec))):
        dict_to_mongo = dict()
        dict_to_mongo["_id"] = i
        tituloCientifico = list_reec[i]["informacion"].get("tituloCientifico", "tituloCientifico not found")
        indicadionPublica = list_reec[i]["informacion"].get("indicacionPublica", "indicacionPublica not found")
        indicacionCientifica = list_reec[i]["informacion"].get("indicacionCientifica", "indicacionCientifica not found")
        criteriosInclusion = list_reec[i]["informacion"].get("criteriosInclusion", "criteriosInclusion not found")
        criteriosExclusion = list_reec[i]["informacion"].get("criteriosExclusion", "criteriosExclusion not found")
        variablesPrincipales = list_reec[i]["informacion"].get("variablesPrincipales", "variablesPrincipales not found")
        variablesSecundarias = list_reec[i]["informacion"].get("variablesSecundarias", "variablesSecundarias not found")
        objetivoPrincipal = list_reec[i]["informacion"].get("objetivoPrincipal", "objetivoPrincipal not found")
        objetivoSecundario = list_reec[i]["informacion"].get("objetivoSecundario", "objetivoSecundario not found")
        momentosPrincipales = list_reec[i]["informacion"].get("momentosPrincipales", "momentosPrincipales not found")
        momentosSecundarios = list_reec[i]["informacion"].get("momentosSecundarios", "momentosSecundarios not found")
        justificacion  = list_reec[i]["informacion"].get("justificacion", "justificacion not found")


        # Search number and fields of not founds.
        list_of_strings = [tituloCientifico, indicadionPublica, indicacionCientifica, 
                            criteriosInclusion, criteriosExclusion, variablesPrincipales,
                            variablesSecundarias, objetivoPrincipal, objetivoSecundario,
                            momentosPrincipales, momentosSecundarios, justificacion]

        # Search this string in the preivous list of strings
        subs = 'not found'
        # Count Strings with substring String List 
        res = ([i for i in list_of_strings if subs in i])
        # Count the "Not Founds" fields and specify them (put in an array or inside a key of the dict)

        dict_to_mongo["ti_es"] = tituloCientifico
        dict_to_mongo["ab_es"] = '\n '.join([indicadionPublica, indicacionCientifica, 
                                            criteriosInclusion, criteriosExclusion,
                                            variablesPrincipales, variablesSecundarias,
                                            objetivoPrincipal, objetivoSecundario,
                                            momentosPrincipales, momentosSecundarios,
                                            justificacion])
        # List of ELEMENTS NOT FOUND.
        dict_to_mongo["list_elem_not_found"] = res
        # Number of ELEMENTS NOT FOUND.
        dict_to_mongo["num_elem_not_found"] = len(res)

        dict_to_mongo["lang_ab"] = "es"
        dict_to_mongo["lang_ti"] = "es"
        lista_dicts[count] = dict_to_mongo

    return lista_dicts

# Save batch of dicts to json files
def save_dict_to_json_file(dest_file, list_dicts):
    output_file = open(dest_file, 'w', encoding='utf-8')
    for dic in list_dicts:
        output_file.write(unicode(json.dump(dic, output_file)))
        output_file.write("\n")

# Save data to MongoDB
def save_to_mongo(host_name, port_num, database, collection, list_dicts):
    myclient = pymongo.MongoClient(host=host_name, port=int(port_num))
    mydb = myclient[database]
    mycol = mydb[collection]

    try:
        x = mycol.insert_many(list_dicts, ordered=False)
        print("Saved into MongoDB {} records.".format(len(x.inserted_ids)))
    except BulkWriteError as bwe:
        print("Batch Inserted with some errors. May be some duplicates were found and are skipped.")

    
    #print(f"Count is {len(x.inserted_ids)}.")
    

# Main function.
def main(args):
    # Get the id list of the crinical trials to be crawled
    initime = datetime.now()
    
    # Check if to_date is present as argument of the script
    if args.to_date is not None:
        list_trial = reec.get_trials_list(from_date = args.from_date, to_date = args.to_date)
    else:
        list_trial = reec.get_trials_list(from_date = args.from_date)
    
    # Get list of ids.
    ids_list = [i["identificador"] for i in list_trial["estudio"]]
    print("-------------------------------------------------------------------------------")
    print("The crawler is going to download {} elements. It took {} seconds to get this data.".format(len(ids_list), datetime.now() - initime))
    
    # Procces in batches .
    batch_size = 50    
    for i in range(0, len(ids_list), batch_size):
        initime = datetime.now()
        index_ini = i
        index_end = i + batch_size
        print("-------------------------------------------------------------------------------")
        print('Processing files {}-{} out of {}. '.format(index_ini, index_end, len(ids_list)))
        print("-------------------------------------------------------------------------------")
        
        # Create the batch.
        batch = ids_list[index_ini:index_end]

        # Get the reec records details.
        lista_reec = dict()
        for j in batch:
            lista_reec[j] = reec.get_trial_details(j)
        
        # Process the elements taken from the API to the previous REEC format in the TeMU team at BSC.   
        list_reec_processed = process_batch_reec_records(lista_reec)
        
        # Define paths and file name.
        dest_file = "reec_temp_" + str(index_ini) + "_" + str(index_end) + ".json"
        dest_path = args.datapath + "/" + dest_file
        
        # Save to json file.
        save_dict_to_json_file(dest_path, list_reec_processed)
        print("File {} saved into {}.".format(dest_file,args.datapath))

        # If specified in the arguments, save to Mongo.
        if(args.out =="mongo"):
            # Save to mongo
            print("Saving records to Mongo: Database - {}, Collection - {}.".format(args.database, args.collection))
            save_to_mongo(args.host, args.port, args.database, args.collection, list_reec_processed)
            
        print("It took {} seconds. \n".format(datetime.now()-initime))


if __name__ == '__main__':
    # Parse the input arguments
    parser = argparse.ArgumentParser()

    # PArse arguments
    parser.add_argument('--from_date', required = True, help = "Date from which you want to start downloading data")
    parser.add_argument('--to_date', help = "Date to which you want to download data")
    parser.add_argument('-o', '--out', metavar = [MODE_DATA, MODE_MONGO], default='file', required = True, help = "To define if the program needs to save the data in a json file or to a mongo collection")
    parser.add_argument('-dpath', '--datapath', default ="/data", help = "Data path where to save the generated json files" )
    parser.add_argument('--host', help = "Define the Mongo host")
    parser.add_argument('--port', help = "Define the Mongo port")
    parser.add_argument('--database', help = "Define the MongoDB database name")
    parser.add_argument('--collection', help = "Define the MongoDB collection name")

    # Assign to variable
    args = parser.parse_args()

    if (args.out != "mongo" and (args.host or args.port or args.database or args.collection)):
        parser.error('--host and --port can only be set when --out=mongo.')
  
    # Get the current working directory (CWD)   
    cwd = os.getcwd() 
    if args.datapath == "/data": #datapath is the standard value
        args.datapath = cwd + args.datapath

    # Execute main
    main(args)