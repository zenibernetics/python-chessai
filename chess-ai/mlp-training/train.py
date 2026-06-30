import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
'''
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.is_available())
'''

BATCH_SIZE = 1024
EPOCHS = 500
LR = 1e-3


class ChessDataset(Dataset):
    def __init__(self, files):
        X_list, Y_list = [], []
        for f in files:
            data = np.load(f)
            X_list.append(data["X"])
            Y_list.append(data["Y"])

        X_raw = np.concatenate(X_list, axis=0)
        Y_raw = np.concatenate(Y_list, axis=0)

        # 先截断到 ±4000（与之前一致，其实可以不做，因为要过滤）
        Y_raw = np.clip(Y_raw, -4000, 4000)

        # 只保留绝对值 ≤ 3000 的样本（抛弃将杀局面）
        keep = np.abs(Y_raw) <= 3000
        self.X = X_raw[keep]
        self.Y = Y_raw[keep]

        print(f"过滤前样本数：{len(Y_raw)}，过滤后：{len(self.Y)}")



    def __len__(self):
        return len(self.X)

    def __getitem__(self, i):
        return (
            torch.tensor(self.X[i], dtype=torch.float32),
            torch.tensor(self.Y[i], dtype=torch.float32),
        )


class MLP(nn.Module):
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


def load_model(path):
    model = MLP().to(DEVICE)
    try:
        state = torch.load(path, map_location=DEVICE)
        model.load_state_dict(state)
        print("resumed from checkpoint")
    except Exception as e:
        print(f"加载失败，具体错误: {e}")
        print("train from scratch")
    return model


def main():

    dataset = ChessDataset(["sfself_6d_0000.npz","sfself_6d_0001.npz","sfself_6d_0002.npz","sfself_6d_0003.npz",
                            "sfself_6d_0004.npz","sfself_6d_0005.npz","sfself_6d_0006.npz","sfself_6d_0007.npz",
                            "sfself_6d_0008.npz","sfself_6d_0009.npz","sfself_6d_0010.npz","sfself_6d_0011.npz",
                            "sfself_6d_0012.npz","sfself_6d_0013.npz","sfself_6d_0014.npz","sfself_6d_0015.npz",
                            "sfself_6d_0016.npz","sfself_6d_0017.npz","sfself_6d_0018.npz","sfself_6d_0019.npz",
                            "sfself_6d_0020.npz","sfself_6d_0021.npz","sfself_6d_0022.npz","sfself_6d_0023.npz",
                            "sfself_6d_0024.npz",
                            "sfself_5d_0000.npz","sfself_5d_0001.npz","sfself_5d_0002.npz","sfself_5d_0003.npz",
                            ])

    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    model = load_model("tiny_mlp.pth")

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()

    for epoch in range(EPOCHS):

        total = 0

        for x, y in loader:

            x = x.to(DEVICE)
            y = y.to(DEVICE).unsqueeze(1)

            pred = model(x)
            loss = loss_fn(pred, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total += loss.item()

        print(f"epoch {epoch+1} loss={total/len(loader):.0f}")

        torch.save(model.state_dict(), "tiny_mlp.pth")


if __name__ == "__main__":
    main()