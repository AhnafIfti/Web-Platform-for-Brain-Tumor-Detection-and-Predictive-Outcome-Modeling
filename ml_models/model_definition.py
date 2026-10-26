def build_model():
    import segmentation_models_pytorch as smp
    # A full trained state_dict supplies encoder weights; never fetch ImageNet weights.
    return smp.Unet(encoder_name='tu-swin_tiny_patch4_window7_224',
                    encoder_weights=None, in_channels=2, classes=3, activation=None)
