#!/usr/bin/env python3

import argparse
import yaml
import click
import os
import pandas as pd

def readConfig(data):
    dnsprovider = {}
    infraprovider = {}
   
    # Loading the YAML configuration
    cf = open(data, "rt")
    try:
        config = yaml.safe_load(cf)
    except yaml.YAMLError:
        print('Invalid YAML file!')
        exit(1)

    # Reading the configuration file for DNS providers 
    try:
        if "dns" in config.keys():  
            for i in config["dns"]:
                if config["dns"][i]["enabled"] == True:
                    dnsprovider[i] = {"credentials": config["dns"][i]["credentials"], "accounts": config["dns"][i]["accounts"]}
                    if None in dnsprovider[i].values():
                        raise KeyError
        else:
            click.echo("Invalid Configuration! please check that DNS provider is configured.")
        
        if dnsprovider == {}:
            click.echo("Invalid Configuration! please check atleast one DNS provider needs to be enabled.")

        if None in dnsprovider.values():
                raise KeyError

    except KeyError:
        click.echo("Invalid Configuration! please check the DNS section in configuration file.")
        exit(1)

    # Reading the configuration file for Infrastructure
    try:
        if "infra" in config.keys():  
            for i in config["infra"]:
                if config["infra"][i]["enabled"] == True:
                    infraprovider[i] = {"credentials": config["infra"][i]["credentials"], "accounts": config["infra"][i]["accounts"]}
                    if None in infraprovider[i].values():
                        raise KeyError
        else:
            click.echo("Invalid Configuration! please check that Infrastructure provider is configured.")

        if infraprovider == {}:
            click.echo("Invalid Configuration! please check atleast one Infrastructure provider needs to be enabled.")
        
        if None in infraprovider.values():
                raise KeyError

    except KeyError:
        click.echo("Invalid Configuration! please check the Infrastructure section in configuration file.")
        exit(1)

    return dnsprovider, infraprovider

def main():
    CLI_PROMPT="""        
        __ _           _                 _        _                            
        / _(_)         | |               | |      | |                           
        | |_ _ _ __   __| |_ __ ___  _   _| |_ __ _| | _____  _____   _____ _ __ 
        |  _| | '_ \ / _` | '_ ` _ \| | | | __/ _` | |/ / _ \/ _ \ \ / / _ \ '__|
        | | | | | | | (_| | | | | | | |_| | || (_| |   <  __/ (_) \ V /  __/ |   
        |_| |_|_| |_|\__,_|_| |_| |_|\__, |\__\__,_|_|\_\___|\___/ \_/ \___|_|   
                                    __/ |                                      
                                    |___/                                       
        """
    
    click.secho(CLI_PROMPT, bold=True, fg='green')

    # Read the arguments that have been passed in to the program.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-file",
        default=os.getcwd() + "/findmytakeover.config",
        type=str,
        help="Enter the path to the configuration file that you want the tool to use.",
    )
    args = parser.parse_args()
    click.echo("Reading the config from file - " + args.config_file)
    dns, infra = readConfig(args.config_file)
 
    recordlist = []
    infrastructurelist = []

    # parse the provider and invoke appropriate collector
    for d in dns:
        if d == "aws":
            from collector.aws import aws
            awsdns = aws.dns(dns["aws"]["accounts"], dns["aws"]["credentials"])
            for f in awsdns:
                recordlist.append(["Amazon Web Services", f[0], f[1], f[2]])

        elif d == "gcp":
            from collector.gcp import gcp
            gcpdns = gcp.dns(dns["gcp"]["accounts"], dns["gcp"]["credentials"])
            for f in gcpdns:
                recordlist.append(["Google Cloud Platform", f[0], f[1], f[2]])
            
        elif d == "azure":
            from collector.msazure import azure
            azuredns = azure.dns(dns["azure"]["accounts"], dns["azure"]["credentials"])
            for f in azuredns:
                recordlist.append(["Microsoft Azure", f[0], f[1], f[2]])
        else:
            print("The DNS provider configured" + d + "is not supported by the tool. Please read the documentation.")

    records = pd.DataFrame(recordlist, columns=['csp', 'account', 'dnskey', 'dnsvalue'])
    
    for i in infra:
        if i == "aws":
            from collector.aws import aws
            awsinfra = aws.infra(infra["aws"]["accounts"], infra["aws"]["credentials"])
            for f in awsinfra:
                infrastructurelist.append(["Amazon Web Services", f[0], f[1], f[2]])

        elif i == "gcp":
            from collector.gcp import gcp
            gcpinfra = gcp.infra(infra["gcp"]["accounts"], infra["gcp"]["credentials"])
            for f in gcpinfra:
                infrastructurelist.append(["Google Cloud Platform", f[0], f[1], f[2]])

        elif i == "azure":
            from collector.msazure import azure
            azureinfra = azure.infra(dns["azure"]["accounts"], dns["azure"]["credentials"])
            for f in azureinfra:
                infrastructurelist.append(["Microsoft Azure", f[0], f[1], f[2]])
        else:
            print("The Infrastructure provider configured" + d + "is not supported by the tool. Please read the documentation.")

    infrastructure = pd.DataFrame(infrastructurelist, columns=['csp', 'account', 'service', 'value'])
    
    result = pd.merge(records, infrastructure, left_on='dnsvalue', right_on='value', how='left').fillna(value="")
    
    click.echo("Checking for possible dangling DNS records!")
    print("\n\n\n")

    for i in result.index:
        if result['value'][i] == "":
            click.echo("Found dangling DNS record - " + result["dnskey"][i] + " with the value "+ result["dnsvalue"][i] + " in " + result["csp_x"][i] + " cloud in the account/subscription/project - " + result["account_x"][i])
    
if __name__ == "__main__":
    main()