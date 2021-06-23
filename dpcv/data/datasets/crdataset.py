import torch
import os
import pickle
import glob
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import librosa
from PIL import Image
import random
import numpy as np
from dpcv.data.datasets.transforms import set_crnet_transform


class BimodalData(Dataset):
    def __init__(self, data_root, img_dir, audio_dir, label_file):
        self.data_root = data_root
        self.img_dir = img_dir
        self.audio_dir = audio_dir
        self.img_dir_ls = self.parse_img_dir(img_dir)  # every directory name indeed a video
        self.annotation = self.parse_annotation(label_file)

    def parse_img_dir(self, img_dir):
        img_dir_ls = os.listdir(os.path.join(self.data_root, img_dir))
        # img_dir_ls = [img_dir.replace("_aligned", "") for img_dir in img_dir_ls if "aligned" in img_dir]
        return img_dir_ls

    def parse_annotation(self, label_file):
        label_path = os.path.join(self.data_root, label_file)
        with open(label_path, "rb") as f:
            annotation = pickle.load(f, encoding="latin1")
        return annotation

    def _find_ocean_score(self, index):
        video_name = self.img_dir_ls[index] + ".mp4"
        score = [
            self.annotation["openness"][video_name],
            self.annotation["conscientiousness"][video_name],
            self.annotation["extraversion"][video_name],
            self.annotation["agreeableness"][video_name],
            self.annotation["neuroticism"][video_name],
        ]
        return score

    def __getitem__(self, index):
        raise NotImplementedError

    def __len__(self):
        return 3000  # len(self.img_dir_ls)


class CRNetData(BimodalData):
    def __init__(self, data_root, img_dir, audio_dir, label_file, transform=None):
        super().__init__(data_root, img_dir, audio_dir, label_file)
        self.transform = transform

    def __getitem__(self, idx):
        anno_score = self._find_ocean_score(idx)
        anno_cls_encode = self._cls_encode(anno_score)

        glo_img, loc_img = self.get_imgs(idx)
        wav_aud = self.get_wav_aud(idx)

        if self.transform:
            glo_img = self.transform(glo_img)
            loc_img = self.transform(loc_img)
        wav_aud = torch.as_tensor(wav_aud, dtype=glo_img.dtype)
        anno_score = torch.as_tensor(anno_score, dtype=glo_img.dtype)
        anno_cls_encode = torch.as_tensor(anno_cls_encode)

        sample = {
            "glo_img": glo_img, "loc_img": loc_img,  "wav_aud": wav_aud,
            "reg_label": anno_score, "cls_label": anno_cls_encode
        }
        return sample

    @staticmethod
    def _cls_encode(score):
        index = []
        for v in score:
            if 0 < v < 0.5:
                index.append(0)
            elif 0.5 <= v < 0.6:
                index.append(1)
            elif 0.6 <= v < 0.7:
                index.append(2)
            else:
                index.append(3)
        one_hot_cls = np.eye(4)[index]
        return one_hot_cls

    def get_imgs(self, idx):
        glo_img_dir = self.img_dir_ls[idx]
        loc_img_dir = glo_img_dir + "_aligned"

        loc_img_dir_path = os.path.join(self.data_root, self.img_dir + "_face", loc_img_dir)
        loc_imgs = glob.glob(loc_img_dir_path + "/*.bmp")

        separate = [idx for idx in range(0, 96, 3)]  # according to the paper sample 32 frames per video
        img_index = random.choice(separate)
        loc_img_pt = loc_imgs[img_index]
        glo_img_pt = self._match_img(loc_img_pt)

        loc_img_arr = Image.open(loc_img_pt).convert("RGB")
        glo_img_arr = Image.open(glo_img_pt).convert("RGB")

        return glo_img_arr, loc_img_arr

    @staticmethod
    def _match_img(loc_img_pt):
        img_dir = os.path.dirname(loc_img_pt).replace("_face", "").replace("_aligned", "")
        img_name, _ = os.path.basename(loc_img_pt).split(".")
        img_id = int(img_name[-3:])
        glo_img_name = "frame" + str(img_id) + ".jpg"
        return os.path.join(img_dir, glo_img_name)

    def get_wav_aud(self, index):
        img_dir_name = self.img_dir_ls[index] + ".wav"
        wav_path = os.path.join(self.data_root, self.audio_dir, img_dir_name)
        wav_ft = librosa.load(wav_path, 16000)[0][None, None, :]
        if wav_ft.shape[-1] < 244832:
            wav_temp = np.zeros((1, 1, 244832))
            wav_temp[..., :wav_ft.shape[-1]] = wav_ft
            return wav_temp
        return wav_ft


def make_data_loader(cfg, mode=None):
    # assert (mode in ["train", "val"]), " 'mode' only supports 'train' and 'val'"
    transforms = set_crnet_transform()
    dataset = CRNetData(
        "../datasets",
        "ImageData/trainingData",
        "VoiceData/trainingData",
        "annotation_training.pkl",
        transforms
    )
    data_loader = DataLoader(
        dataset=dataset,
        batch_size=2,
        shuffle=True,
        num_workers=0  # cfg.NUM_WORKS
    )
    return data_loader


if __name__ == "__main__":
    trans = set_crnet_transform()
    data_set = CRNetData(
        "../../../datasets",
        "ImageData/trainingData",
        "VoiceData/trainingData",
        "annotation_training.pkl",
        trans
    )
    # print(len(data_set))
    print(data_set[2])
    for item in data_set[2].values():
        print(item.shape)
    # # print(data_set._statistic_img_sample(1))
    # # print(data_set._get_wav_sample(1))


    # loader = make_data_loader("")
    # for i, sample in enumerate(loader):
    #     if i > 5:
    #         break
    #     for item in sample.values():
    #         print(item.shape)
