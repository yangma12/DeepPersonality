#!/usr/bin/env bash

CONFIG=$1
echo "TRAIN FROM CONFIG: $CONFIG"
python run_exp.py -c "$CONFIG"