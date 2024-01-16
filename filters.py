def pad_zero(value):
    value=str(value)
    return value.zfill(7) if len(value) < 7 else value
