# ==============================================================================
# Google Colab Vision Model Training Script (Healthy vs. Damaged)
# ==============================================================================
# Instructions:
# 1. Zip local dataset: zip -r dataset.zip dataset/
# 2. Upload dataset.zip to Google Colab files
# 3. Run this script in a GPU runtime (T4 GPU)
# 4. Downloads: vision_model.h5 and vision_training_plot.png
# ==============================================================================

import os
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from google.colab import files

# 1. Unzip the Dataset using Linux native command
print("Unzipping dataset.zip...")
os.system("unzip -q -o dataset.zip -d .")
print("Dataset extracted successfully!")

# Verify folders exist
DATASET_DIR = "dataset"
TRAIN_DIR = os.path.join(DATASET_DIR, "train")
VAL_DIR = os.path.join(DATASET_DIR, "val")
TEST_DIR = os.path.join(DATASET_DIR, "test")

print("Train classes:", os.listdir(TRAIN_DIR))
print("Val classes:", os.listdir(VAL_DIR))
print("Test classes:", os.listdir(TEST_DIR))

IMG_SIZE = (224, 224)
BATCH_SIZE = 16

# 2. Load Datasets (Healthy = 0, Damaged = 1)
train_ds = tf.keras.utils.image_dataset_from_directory(
    TRAIN_DIR,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="binary",
    class_names=["healthy", "damaged"],
    shuffle=True
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    VAL_DIR,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="binary",
    class_names=["healthy", "damaged"],
    shuffle=False
)

test_ds = tf.keras.utils.image_dataset_from_directory(
    TEST_DIR,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    label_mode="binary",
    class_names=["healthy", "damaged"],
    shuffle=False
)

# Optimize pipeline speed
train_ds = train_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
val_ds = val_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
test_ds = test_ds.prefetch(buffer_size=tf.data.AUTOTUNE)

# 3. Model Architecture (MobileNetV2 Transfer Learning)
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.2),
    layers.RandomZoom(0.1),
])

# Load pretrained MobileNetV2 without classification head
base_model = MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights="imagenet"
)
base_model.trainable = False  # Freeze pretrained weights

# Build complete pipeline
inputs = tf.keras.Input(shape=(224, 224, 3))
x = data_augmentation(inputs)
x = layers.Rescaling(1.0 / 255)(x)  # Normalize pixels to [0, 1]
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dropout(0.2)(x)
# Sigmoid outputs probability: 0.0 = Healthy, 1.0 = Damaged
outputs = layers.Dense(1, activation="sigmoid")(x)

model = models.Model(inputs, outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# 4. Train the Model
EPOCHS = 15

callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=4,
        restore_best_weights=True
    )
]

print("\nStarting Training...")
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks
)

# 5. Evaluate on Held-Out Test Set
print("\nEvaluating on Test Set...")
test_loss, test_acc = model.evaluate(test_ds)
print(f"Test Accuracy: {test_acc * 100:.2f}%")
print(f"Test Loss: {test_loss:.4f}")

# 6. Plot & Save Curves for Research Paper
acc = history.history["accuracy"]
val_acc = history.history["val_accuracy"]
loss = history.history["loss"]
val_loss = history.history["val_loss"]

plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(acc, label="Train Accuracy")
plt.plot(val_acc, label="Val Accuracy")
plt.legend(loc="lower right")
plt.title("Training and Validation Accuracy")
plt.xlabel("Epoch")

plt.subplot(1, 2, 2)
plt.plot(loss, label="Train Loss")
plt.plot(val_loss, label="Val Loss")
plt.legend(loc="upper right")
plt.title("Training and Validation Loss")
plt.xlabel("Epoch")

plt.tight_layout()
plt.savefig("vision_training_plot.png", dpi=300)
plt.show()

# 7. Save and Download Model
MODEL_FILENAME = "vision_model.h5"
model.save(MODEL_FILENAME)
print(f"\nModel saved successfully as '{MODEL_FILENAME}'!")

# Download to local computer
files.download(MODEL_FILENAME)
files.download("vision_training_plot.png")
