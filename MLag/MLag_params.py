To include:
- Type/s of model (LM, NN, SVM, RF)
- Type of descriptors:
  - Molecular fingerprints
  - Fingerprints in 1 atom
  - Manual parameters
- If manually compiling parameters:
   - Type of data to retrieve (csv, txt)
- Type of optimizer for the hypergrid parameters of the models
  (i.e. amount of ntrees, amount of bits, etc). Options: SGD, ADAM,
  the one from Gabe's paper, the mixture of SGD and ADAM
- Option to optimize the number of training/set with PCA and k-means
- Option to use PCA with k clusters with your whole data or clusters of data
- Option to keep improving the model (generate new input files
  and start the OPT process using R2 and RMSE until it becomes
  practically constant)
- Option for De Novo structures based on reinforcement learning to
  either get molecules in the lower range or in the higher range
