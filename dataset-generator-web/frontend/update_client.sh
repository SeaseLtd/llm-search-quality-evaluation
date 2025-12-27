#!/bin/bash

rm openapi*.json
curl -o openapi.json "http://localhost:8000/api/v1/openapi.json"

npm run generate-client
