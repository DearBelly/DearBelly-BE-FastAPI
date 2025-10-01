
import torch
import torch.nn as nn
import timm
from torchvision import transforms
from PIL import Image
import json
from pathlib import Path
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class EfficientNetBaseline(nn.Module):
    def __init__(self, num_classes, pretrained=True, dropout=0.2):
        super().__init__()
        logger.info(
            f"Initializing EfficientNetBaseline with num_classes={num_classes}, pretrained={pretrained}, dropout={dropout}")

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

        logger.info(f"Initializing PredictorService with model_path={model_path}, json_path={json_path}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # cuda 모델 확인
        logger.info(f"Using device: {self.device}")

        self.idx2label = self._load_idx2label(json_path)
        self.num_classes = len(self.idx2label)
        logger.info(f"Loaded {self.num_classes} classes")

        self.model = self._load_model(model_path)
        self.transform = transforms.Compose([
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
        ])
        logger.info("PredictorService initialized successfully")

    def _load_idx2label(self, json_path: Path) -> dict:

        # json 제대로 읽었는지 확인
        logger.info(f"Loading idx2label from {json_path}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            idx2label = data.get("idx2label")
            if not idx2label:
                logger.warning("idx2label not found in JSON, generating from samples")
                unique_labels = sorted(set(sample["label"] for sample in data["samples"]))
                idx2label = {str(label): f"K-{label:06d}" for label in unique_labels}
            return idx2label

        # 예외 사항 추가
        except FileNotFoundError:
            logger.error(f"JSON file not found: {json_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading idx2label: {e}", exc_info=True)
            raise

    def _load_model(self, model_path: Path) -> EfficientNetBaseline:
        # model path 확인하기
        logger.info(f"Loading model from {model_path}")

        import __main__
        __main__.EfficientNetBaseline = EfficientNetBaseline

        try:
            object = torch.load(model_path, map_location=self.device, weights_only=False)

            if isinstance(object, nn.Module) :
                # 그 자체로 모델일 때
                model = object.to(self.device)
            elif isinstance(object, dict) :
                # 반환 타입이 state_dict
                state_dict = object
                for k in ['state_dict', 'model_state_dict', 'model']:
                    if k in object and isinstance(object[k], dict):
                        state_dict = object[k]
                        break

                model = EfficientNetBaseline(self.num_classes).to(self.device)

                missing, unexpected = model.load_state_dict(state_dict, strict=False)
                if missing or unexpected:
                    logger.warning(f"[load_state_dict] missing keys: {missing}, unexpected keys: {unexpected}")
            else:
                # type 일치하지 않음
                error_msg = f"Unsupported checkpoint type: {type(object)}"
                logger.error(error_msg)
                raise TypeError(f"Unsupported checkpoint type: {type(object)}")

            # 완료
            model.eval()
            logger.info("Model loaded and set to evaluation mode")
            return model

        except FileNotFoundError:
            logger.error(f"Model file not found: {model_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise


    def predict(self, stream_file: BytesIO) -> tuple[str, str, float]:

        try :
            image = Image.open(stream_file).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.model(input_tensor)
                predicted_idx = torch.argmax(output, dim=1).item()
                confidence = torch.softmax(output, dim=1)[0][predicted_idx].item()

            label = str(predicted_idx)
            pill_name = self.idx2label.get(label, f"Unknown Label: {label}")
            logger.info(f"Prediction completed - pill_name: {pill_name}, label: {label}, confidence: {confidence:.4f}")

            return pill_name, label, confidence
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise


HERE = Path(__file__).resolve().parent.parent
MODEL_PATH = HERE / "models" / "models" / "best_model_0920.pt"
JSON_PATH = HERE / "models" / "models" / "matched_all.json"

predictor_service = PredictorService(MODEL_PATH, JSON_PATH)
