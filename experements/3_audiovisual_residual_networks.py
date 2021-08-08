import torch.nn as nn
import os
import torch.optim as optim
from datetime import datetime
from dpcv.engine.bi_modal_trainer import BiModalTrainer
from dpcv.tools.common import setup_seed, setup_config
from dpcv.tools.logger import make_logger
from dpcv.modeling.networks.audio_visual_residual import get_audiovisual_resnet_model
from dpcv.config.audiovisual_resnet_cfg import cfg
from dpcv.checkpoint.save import save_model, resume_training
from dpcv.data.datasets.audio_visual_data import make_data_loader
from dpcv.tools.common import parse_args
from dpcv.evaluation.summary import TrainSummary


def main(args, cfg):
    setup_seed(12345)
    cfg = setup_config(args, cfg)
    logger, log_dir = make_logger(cfg.RESULT_DIR)
    logger.info("file_name: \n{}\n".format(__file__))

    train_loader = make_data_loader(cfg, mode="train")
    valid_loader = make_data_loader(cfg, mode="valid")

    model = get_audiovisual_resnet_model()
    loss_f = nn.L1Loss()
    optimizer = optim.Adam(model.parameters(), lr=0.0002, betas=(0.5, 0.999), eps=1e-8)
    scheduler = optim.lr_scheduler.MultiStepLR(optimizer, gamma=cfg.FACTOR, milestones=cfg.MILESTONE)

    collector = TrainSummary()
    trainer = BiModalTrainer(cfg, collector, logger)

    start_epoch = cfg.START_EPOCH
    if cfg.RESUME:
        model, optimizer, epoch = resume_training(cfg.RESUME, model, optimizer)
        start_epoch = epoch
        logger.info(f"resume training from {cfg.RESUME}")

    for epoch in range(start_epoch, cfg.MAX_EPOCH):
        # train for one epoch
        trainer.train(train_loader, model, loss_f, optimizer, epoch)
        # eval after training an epoch
        trainer.valid(valid_loader, model, loss_f, epoch)
        # update training lr every epoch
        scheduler.step()

        if collector.model_save:
            save_model(epoch, collector.best_valid_acc, model, optimizer, log_dir, cfg)
            collector.update_best_epoch(epoch)

    collector.draw_epo_info(cfg.MAX_EPOCH - start_epoch, log_dir)
    logger.info(
        "{} done, best acc: {} in :{}".format(
            datetime.strftime(datetime.now(), '%m-%d_%H-%M'), collector.best_valid_acc, collector.best_epoch)
    )


if __name__ == "__main__":
    args = parse_args()
    main(args, cfg)
