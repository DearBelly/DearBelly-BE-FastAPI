
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import json
from pathlib import Path

class LightCNN(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, 3, padding=1)
        self.conv2 = nn.Conv2d(8, 16, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.gap = nn.AdaptiveAvgPool2d((4, 4))
        self.fc1 = nn.Linear(16 * 4 * 4, 64)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.gap(x)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class PredictorService:
    def __init__(self, model_path: Path, json_path: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.idx2label = self._load_idx2label(json_path)
        self.num_classes = len(self.idx2label)
        self.model = self._load_model(model_path)
        self.transform = transforms.Compose([
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
        ])

    def _load_idx2label(self, json_path: Path) -> dict:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        idx2label = data.get("idx2label")
        if not idx2label:
            unique_labels = sorted(set(sample["label"] for sample in data["samples"]))
            idx2label = {str(label): f"K-{label:06d}" for label in unique_labels}
        return idx2label

    def _load_model(self, model_path: Path) -> LightCNN:
        model = LightCNN(num_classes=self.num_classes).to(self.device)
        checkpoint = torch.load(model_path, map_location=self.device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model

    def predict(self, image_path: Path) -> tuple[str, str, float]:
        image = Image.open(image_path).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)
            predicted_idx = torch.argmax(output, dim=1).item()
            confidence = torch.softmax(output, dim=1)[0][predicted_idx].item()

        label = str(predicted_idx)
        pill_name = self.idx2label.get(label, f"Unknown Label: {label}")

        return pill_name, label, confidence


HERE = Path(__file__).resolve().parent.parent
MODEL_PATH = HERE / "models" / "models" / "best_model_0823.pt"
JSON_PATH = HERE / "models" / "models" / "matched_all.json"

predictor_service = PredictorService(MODEL_PATH, JSON_PATH)
