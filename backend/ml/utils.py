from PIL import Image
from torchvision import transforms


def build_transform(image_size=224):
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def load_image(path):
    return Image.open(path).convert("RGB")
