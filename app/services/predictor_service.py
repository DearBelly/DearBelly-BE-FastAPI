
import torch
import torch.nn as nn
import timm
from torchvision import transforms
from PIL import Image
import json
from pathlib import Path
from io import BytesIO

class EfficientNetBaseline(nn.Module):
    def __init__(self, num_classes, pretrained=True, dropout=0.2):
        super().__init__()
        self.backbone = timm.create_model(
            "efficientnet_b3", pretrained=pretrained, num_classes=0, global_pool="avg"
        )
        feat_dim = self.backbone.num_features
        self.bn = nn.BatchNorm1d(feat_dim)
        self.dp = nn.Dropout(dropout)
        self.fc = nn.Linear(feat_dim, num_classes)

    def forward(self, x):
        feats = self.backbone(x)
        feats = self.bn(feats)
        feats = self.dp(feats)
        logits = self.fc(feats)
        return logits

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

    def _load_model(self, model_path: Path) -> EfficientNetBaseline:
        import __main__
        __main__.LightCNN = EfficientNetBaseline

        object = torch.load(model_path, map_location=self.device, weights_only=False)

        if isinstance(object, nn.Module) :
            # 그 자체로 모델일 때
            model = object.to(self.device)
        elif isinstance(object, dict) :
            # 반환 타입이 state_dict
            state_dict = object
            for k in ['state_dict', 'model_state_dict', 'model']:
                if k in object and isinstance(object[k], dict):
                    state_dict[k] = object[k]
                    break

            model = EfficientNetBaseline(self.num_classes).to(self.device)

            missing, unexpected = model.load_state_dict(state_dict, strict=False)
            if missing or unexpected:
                print(f"[load_state_dict] missing keys: {missing}, unexpected keys: {unexpected}")
        else:
            # type 일치하지 않음
            raise TypeError(f"Unsupported checkpoint type: {type(object)}")

        model.eval()
        return model

    def predict(self, stream_file: BytesIO) -> tuple[str, str, float]:
        image = Image.open(stream_file).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)
            predicted_idx = torch.argmax(output, dim=1).item()
            confidence = torch.softmax(output, dim=1)[0][predicted_idx].item()

        label = str(predicted_idx)
        pill_name = self.idx2label.get(label, f"Unknown Label: {label}")

        return pill_name, label, confidence


HERE = Path(__file__).resolve().parent.parent
MODEL_PATH = HERE / "models" / "models" / "best_model_0920.pt"
JSON_PATH = HERE / "models" / "models" / "matched_all.json"

predictor_service = PredictorService(MODEL_PATH, JSON_PATH)
