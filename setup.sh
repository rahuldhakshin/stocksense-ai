#!/bin/bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
mkdir -p data models
python data_pipeline.py
python ml_model.py
echo "Setup complete!"
