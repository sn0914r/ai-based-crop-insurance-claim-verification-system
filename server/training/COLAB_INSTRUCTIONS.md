# Google Colab Training Instructions for Vision Model

Follow these steps whenever you want to retrain the vision model in Google Colab:

## Step 1: Zip the Local Dataset

From the project root on your Mac:

```bash
zip -r dataset.zip dataset/
```

## Step 2: Open Google Colab

1. Go to https://colab.research.google.com/
2. Create a new notebook.
3. Change runtime: `Runtime -> Change runtime type -> T4 GPU -> Save`.

## Step 3: Upload dataset.zip

1. Click the Folder icon (Files) in the left panel.
2. Drag and drop `dataset.zip` into the files area.
3. Wait until the upload completes (file size ~11MB).

## Step 4: Run Training Script

1. Copy the code from `server/experiments/train_vision_colab.py`.
2. Paste it into a Colab cell and execute.
3. The script will automatically:
   - Unzip the dataset
   - Train MobileNetV2 with transfer learning for 15 epochs
   - Evaluate accuracy on the test set
   - Generate `vision_training_plot.png`
   - Download `vision_model.h5` and the plot to your computer

## Step 5: Place the Model in Server

Move the downloaded `vision_model.h5` into:

```text
server/models_saved/vision_model.h5
```
