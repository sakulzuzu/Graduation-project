import os

import numpy as np
import torch
from PIL import Image
from torchvision import models

from ml.utils import build_transform, load_image


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.activations = None
        self.gradients = None
        self.target_layer.register_forward_hook(self._save_activation)
        self.target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _module, _input, output):
        self.activations = output

    def _save_gradient(self, _module, _grad_input, grad_output):
        self.gradients = grad_output[0]

    def generate(self, input_tensor, class_idx=None):
        self.model.zero_grad()
        output = self.model(input_tensor)
        if class_idx is None:
            class_idx = int(output.argmax(dim=1).item())
        score = output[:, class_idx]
        score.backward()
        grads = self.gradients[0]
        activations = self.activations[0]
        weights = grads.mean(dim=(1, 2))
        cam = (weights[:, None, None] * activations).sum(dim=0)
        cam = torch.relu(cam)
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        return cam.detach().cpu().numpy()


def overlay_heatmap(image, cam, alpha=0.4):
    cam_resized = Image.fromarray((cam * 255).astype(np.uint8)).resize(image.size)
    cam_array = np.array(cam_resized) / 255.0
    heatmap = np.zeros((image.size[1], image.size[0], 3), dtype=np.uint8)
    heatmap[..., 0] = (cam_array * 255).astype(np.uint8)
    overlay = Image.blend(image.convert("RGB"), Image.fromarray(heatmap), alpha=alpha)
    return overlay


class ModelService:
    def __init__(self, weights_path, model_name="resnet50"):
        self.weights_path = weights_path
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.transform = build_transform()
        self.model = self._load_model()
        self.grad_cam = GradCAM(self.model, self.model.layer4)

    def _load_model(self):
        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        num_features = model.fc.in_features
        model.fc = torch.nn.Linear(num_features, 2)
        if os.path.exists(self.weights_path):
            state = torch.load(self.weights_path, map_location=self.device)
            model.load_state_dict(state)
        model.to(self.device)
        model.eval()
        return model

    def predict(self, image_path, processed_dir, heatmap_dir):
        image = load_image(image_path)
        processed_path = self._save_processed(image, image_path, processed_dir)
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(input_tensor)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
        class_idx = int(np.argmax(probs))
        cam = self.grad_cam.generate(input_tensor, class_idx=class_idx)
        heatmap_image = overlay_heatmap(image, cam)
        heatmap_path = self._save_heatmap(heatmap_image, heatmap_dir)
        return {
            "prob_benign": float(probs[0]),
            "prob_malignant": float(probs[1]),
            "predicted_label": "benign" if class_idx == 0 else "malignant",
            "processed_path": processed_path,
            "heatmap_path": heatmap_path,
        }

    def _save_processed(self, image, image_path, processed_dir):
        os.makedirs(processed_dir, exist_ok=True)
        base = os.path.basename(image_path)
        name, _ext = os.path.splitext(base)
        filename = f"processed_{name}.jpg" if name else f"processed_{os.urandom(8).hex()}.jpg"
        path = os.path.join(processed_dir, filename)
        image.resize((224, 224)).save(path, format="JPEG")
        return path

    def _save_heatmap(self, heatmap_image, heatmap_dir):
        os.makedirs(heatmap_dir, exist_ok=True)
        filename = f"heatmap_{os.urandom(8).hex()}.jpg"
        path = os.path.join(heatmap_dir, filename)
        heatmap_image.save(path, format="JPEG")
        return path
