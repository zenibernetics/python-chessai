import numpy as np
import torch
import torch.nn as nn

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

class TinyNNUE(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(781, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )

    def forward(self, x):
        return self.net(x)

data = np.load("sfself_6d_0025.npz")

X_raw = torch.tensor(data["X"], dtype=torch.float32)
Y_raw = torch.tensor(data["Y"], dtype=torch.float32)

# 只保留标签绝对值 ≤ 3000 的样本（丢弃将死局面）
keep = (Y_raw.abs() <= 3000)
X = X_raw[keep]
Y = Y_raw[keep]

# 验证形状是否一致
print(f"过滤后 X 形状: {X.shape}, Y 形状: {Y.shape}")
assert X.shape[0] == Y.shape[0], "X 和 Y 的样本数不一致！"

print(f"原始样本数: {len(Y_raw)}, 过滤后样本数: {len(Y)}")

model = TinyNNUE().to(DEVICE)
model.load_state_dict(
    torch.load("tiny_mlp.pth", map_location=DEVICE)
)
model.eval()

with torch.no_grad():
    # 注意这里必须是 X，不是 X_raw
    pred = model(X.to(DEVICE)).cpu().squeeze()
    mae = (pred - Y).abs().mean()

    print("\n    真实值     预测值")
    print("-" * 30)

    num_samples = len(Y)
    if num_samples > 0:
        random_indices = np.random.choice(num_samples, size=min(20, num_samples), replace=False)
        for i in random_indices:
            print(f"{Y[i]:8.0f} {pred[i]:8.0f}")
    else:
        print("没有满足条件的样本！")

print(f"\nMAE = {mae.item():.0f}")