from sklearn.linear_model import LogisticRegression


def train_baseline_calibrator(features, labels):
    model = LogisticRegression(max_iter=2000, random_state=20260611)
    return model.fit(features, labels)
