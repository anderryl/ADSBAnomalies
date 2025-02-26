import numpy as np
from pyod.models.iforest import IForest
import matplotlib.pyplot as plt
from sklearn import tree
import math

file = open("frames.csv")
frames = file.read()
file.close()
frames = [np.array([float(col) for col in row.split(",") if len(col) > 0]) for row in frames.strip().split("\n")]
frames = [frame for frame in frames if frame[2] < 20000]
x = np.array(frames)
forest = IForest(max_samples=len(x))
forest.fit(x)
print(forest.feature_importances_)
outliers = forest.predict(x)
print("Outlier Predictions:")
plt.figure()
plt.scatter(x[:, 1], x[:, 0],  c=outliers, cmap='coolwarm', s=50)
plt.show()
plt.figure()
plt.scatter(x[:, 3], x[:, 2], c=outliers, cmap='coolwarm', s=50)
plt.show()

classifier = tree.DecisionTreeClassifier(max_depth=4)
classifier.fit(x, outliers)
tree.plot_tree(classifier)
print(tree.export_text(classifier, class_names=["normal", "anomaly"], feature_names=["latitude", "longitude", "altitude", "climb gradient"]))
