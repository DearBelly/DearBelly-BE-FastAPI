import json
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms

from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "best_model_0823.pt"
json_path = HERE / 'matched_all.json'

saved_model = torch.load(MODEL_PATH, weights_only=False)


#  1. 모델 클래스 정의 (간단한 LightCNN 예시)
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

# idx2label 로딩 (없으면 자동 생성)
def load_idx2label_from_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    idx2label = data.get("idx2label")

    if not idx2label:
        unique_labels = sorted(set(sample["label"] for sample in data["samples"]))
        idx2label = {str(label): f"K-{label:06d}" for label in unique_labels}
    return idx2label


#메인 파이프라인
def predict(model_path, image_path):
    # 장치 설정
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f" 디바이스: {device}")

    # 전처리 transform
    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
    ])

    # idx2label 로드
    idx2label = load_idx2label_from_json(json_path)
    num_classes = 492  #(모델 학습 기준과 일치)

    if num_classes == 0:
        raise ValueError(" num_classes = 0, idx2label이 비어 있음")

    # 모델 로드
    model = LightCNN(num_classes=num_classes).to(device)
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # 이미지 로딩 및 예측
    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
      output = model(input_tensor)
      predicted_idx = torch.argmax(output, dim=1).item()
      confidence = torch.softmax(output, dim=1)[0][predicted_idx].item()  # confidence 계산 추가


    # 라벨 매핑
    pill_name = idx2label.get(str(predicted_idx), f"Unknown Label: {predicted_idx}")
    # 모델의 직접 판단 결과 출력
    print(f"\n 모델 예측 라벨: {predicted_idx}")
    print(f" 약 코드 또는 이름: {pill_name}")
    print(f"확신 정도 (softmax): {confidence:.4f}")

    return pill_name