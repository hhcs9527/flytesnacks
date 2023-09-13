# %% [markdown]
# (structured_dataset_example)=
#
# # Structured Dataset
#
# ```{eval-rst}
# .. tags:: DataFrame, Basic, Data
# ```
#
# Structured dataset is a superset of Flyte Schema.
#
# The `StructuredDataset` Transformer can write a dataframe to BigQuery, s3, Snowflake, or any storage by registering new structured dataset encoder and decoder.
#
# Flytekit makes it possible to return or accept a {py:class}`pandas.DataFrame` which is automatically
# converted into Flyte's abstract representation of a structured dataset object.
#
# This example explains how a structured dataset can be used with the Flyte entities.

# %% [markdown]
# Let's import the necessary dependencies.
# %%
import os
import typing

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from flytekit import FlyteContext, StructuredDatasetType, kwtypes, task, workflow
from flytekit.models import literals
from flytekit.models.literals import StructuredDatasetMetadata
from flytekit.types.schema import FlyteSchema
from flytekit.types.structured.structured_dataset import (
    PARQUET,
    StructuredDataset,
    StructuredDatasetDecoder,
    StructuredDatasetEncoder,
    StructuredDatasetTransformerEngine,
)
from typing_extensions import Annotated

# %% [markdown]
# We define the columns types for schema and `StructuredDataset`.
# %%
superset_cols = kwtypes(Name=str, Age=int, Height=int)
subset_cols = kwtypes(Age=int)


# %% [markdown]
# We define two tasks, one returns a pandas DataFrame and the other a `FlyteSchema`.
# Flyte serializes the DataFrames to an intermediate format, a parquet file, before sending them to the other tasks.
# %%
@task
def get_df(a: int) -> Annotated[pd.DataFrame, superset_cols]:
    """
    Generate a sample dataframe
    """
    return pd.DataFrame({"Name": ["Tom", "Joseph"], "Age": [a, 22], "Height": [160, 178]})


@task
def get_schema_df(a: int) -> FlyteSchema[superset_cols]:
    """
    Generate a sample dataframe
    """
    s = FlyteSchema()
    s.open().write(pd.DataFrame({"Name": ["Tom", "Joseph"], "Age": [a, 22], "Height": [160, 178]}))
    return s


# %% [markdown]
# Next, we define a task that opens a structured dataset by calling `all()`.
# When we invoke `all()`, the Flyte engine downloads the parquet file on S3, and deserializes it to `pandas.dataframe`.
#
# :::{note}
# - Despite the input type of the task being `StructuredDataset`, it can also accept FlyteSchema as input.
# - The code may result in runtime failures if the columns do not match.
# :::
# %%
@task
def get_subset_df(df: Annotated[StructuredDataset, subset_cols]) -> Annotated[StructuredDataset, subset_cols]:
    df = df.open(pd.DataFrame).all()
    df = pd.concat([df, pd.DataFrame([[30]], columns=["Age"])])
    # When specifying a BigQuery or Snowflake URI for a StructuredDataset, flytekit exports a Pandas DataFrame to a table in BigQuery or Snowflake.
    return StructuredDataset(dataframe=df)


# %% [markdown]
# ## StructuredDataset with `uri` Argument
#
# Both Snowflake and BigQuery `uri` allows you to load and retrieve data from cloud using the `uri`.
# The `uri` comprises of the bucket name and the filename prefixed with `bq://` for BigQuery and `snowflake://` for Snowflake.
# If you specify in either BigQuery or Snowflake `uri` for StructuredDataset, it will create a table in the location specified by the `uri`.
# The `uri` in StructuredDataset reads from or writes to S3, GCP, BigQuery, Snowflake or any storage.
# Let's understand how to convert a pandas DataFrame to a BigQuery or Snowflake table and vice-versa through an example.
#
# Before writing DataFrame to a BigQuery table,
#
# 1. Create a [GCP account](https://cloud.google.com/docs/authentication/getting-started) and create a service account.
# 2. Create a project and add the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to your .bashrc file.
# 3. Create a dataset in your project.

# Before writing DataFrame to a Snowflake table,
#
# 1. Create a [Snowflake account](https://signup.snowflake.com/) and create a service account.
# 2. Create a dataset in your project.
# 3. Use [Key Pair Authentication](https://docs.snowflake.com/en/user-guide/key-pair-auth) to setup the connections with Snowflake.
# 4. run the following command to setup the secret
# ```bash
# kubectl create secret generic snowflake --namespace=flyte --from-literal=private_key={your_private_key_above}
# ```
# %% [markdown]
# Import the dependencies.
# %%
import pandas as pd  # noqa: E402
from flytekit import task  # noqa: E402
from flytekit.types.structured import StructuredDataset  # noqa: E402


# %% [markdown]
# Define a task that converts a pandas DataFrame to a BigQuery table.
# %%
@task
def pandas_to_bq() -> StructuredDataset:
    # create a pandas dataframe
    df = pd.DataFrame({"Name": ["Tom", "Joseph"], "Age": [20, 22]})
    # convert the dataframe to StructuredDataset
    return StructuredDataset(dataframe=df, uri="bq://sample-project-1-352610.sample_352610.test1")


# %% [markdown]
# Define a task that converts a pandas DataFrame to a Snowflake table.
# %%
@task
def pandas_to_sf() -> StructuredDataset:
    # create a pandas dataframe
    df = pd.DataFrame({"Name": ["Tom", "Joseph"], "Age": [20, 22]})
    # convert the dataframe to StructuredDataset
    return StructuredDataset(dataframe=df, uri="snowflake://<user>:<your_account>/<database>/<schema>/<warehouse>/<table>")


# %% [markdown]
# :::{note}
# The BigQuery uri's format is `bq://<project_name>.<dataset_name>.<table_name>`.
# :::

# %% [markdown]
# Define a task that converts the BigQuery table to a pandas DataFrame.
# %%
@task
def bq_to_pandas(sd: StructuredDataset) -> pd.DataFrame:
    # convert to pandas dataframe
    return sd.open(pd.DataFrame).all()

# %% [markdown]
# :::{note}
# The Snowflake uri's format is `snowflake://<user>:<your_account>/<database>/<schema>/<warehouse>/<table>`.
# :::

# %% [markdown]
# Define a task that converts the Snowflake table to a pandas DataFrame.
# %%
@task
def sf_to_pandas(sd: StructuredDataset) -> pd.DataFrame:
    # convert to pandas dataframe
    return sd.open(pd.DataFrame).all()


# %% [markdown]
# :::{note}
# Flyte creates the table inside the dataset in the project upon BigQuery query execution.
# :::

# %% [markdown]
# Trigger the tasks locally.
# %%
if __name__ == "__main__":
    obj_bq_1 = bq_to_pandas(sd=StructuredDataset(uri="bq://sample-project-1-352610.sample_352610.test1"))
    obj_bq_2 = pandas_to_bq()

    obj_sf_1 = sf_to_pandas(sd=StructuredDataset(uri="snowflake://<user>:<your_account>/<database>/<schema>/<warehouse>/<table>"))
    obj_sf_2 = pandas_to_sf()


# %% [markdown]
# ## NumPy Encoder and Decoder
#
# `StructuredDataset` ships with an encoder and a decoder that handles the conversion of a Python value to a Flyte literal and vice-versa, respectively.
# Let's understand how to write them by defining a NumPy encoder and decoder, which helps use NumPy array as a valid type within structured datasets.

# %% [markdown]
# ### NumPy Encoder
#
# We extend `StructuredDatasetEncoder` and implement the `encode` function.
# The `encode` function converts NumPy array to an intermediate format (parquet file format in this case).
# %%
class NumpyEncodingHandlers(StructuredDatasetEncoder):
    def encode(
        self,
        ctx: FlyteContext,
        structured_dataset: StructuredDataset,
        structured_dataset_type: StructuredDatasetType,
    ) -> literals.StructuredDataset:
        df = typing.cast(np.ndarray, structured_dataset.dataframe)
        name = ["col" + str(i) for i in range(len(df))]
        table = pa.Table.from_arrays(df, name)
        path = ctx.file_access.get_random_remote_directory()
        local_dir = ctx.file_access.get_random_local_directory()
        local_path = os.path.join(local_dir, f"{0:05}")
        pq.write_table(table, local_path)
        ctx.file_access.upload_directory(local_dir, path)
        return literals.StructuredDataset(
            uri=path,
            metadata=StructuredDatasetMetadata(structured_dataset_type=StructuredDatasetType(format=PARQUET)),
        )


# %% [markdown]
# ### NumPy Decoder
#
# Next we extend `StructuredDatasetDecoder` and implement the `decode` function.
# The `decode` function converts the parquet file to a `numpy.ndarray`.
# %%
class NumpyDecodingHandlers(StructuredDatasetDecoder):
    def decode(
        self,
        ctx: FlyteContext,
        flyte_value: literals.StructuredDataset,
        current_task_metadata: StructuredDatasetMetadata,
    ) -> np.ndarray:
        local_dir = ctx.file_access.get_random_local_directory()
        ctx.file_access.get_data(flyte_value.uri, local_dir, is_multipart=True)
        table = pq.read_table(local_dir)
        return table.to_pandas().to_numpy()


# %% [markdown]
# ### NumPy Renderer
#
# Create a default renderer for numpy array, then flytekit will use this renderer to
# display schema of numpy array on flyte deck.
# %%
class NumpyRenderer:
    """
    The schema of Numpy array are rendered as an HTML table.
    """

    def to_html(self, df: np.ndarray) -> str:
        assert isinstance(df, np.ndarray)
        name = ["col" + str(i) for i in range(len(df))]
        table = pa.Table.from_arrays(df, name)
        return pd.DataFrame(table.schema).to_html(index=False)


# %% [markdown]
# Finally, we register the encoder, decoder, and renderer with the `StructuredDatasetTransformerEngine`.
# %%
StructuredDatasetTransformerEngine.register(NumpyEncodingHandlers(np.ndarray, None, PARQUET))
StructuredDatasetTransformerEngine.register(NumpyDecodingHandlers(np.ndarray, None, PARQUET))
StructuredDatasetTransformerEngine.register_renderer(np.ndarray, NumpyRenderer())


# %% [markdown]
# You can now use `numpy.ndarray` to deserialize the parquet file to NumPy and serialize a task's output (NumPy array) to a parquet file.

# %% [markdown]
# Let's define a task to test the above functionality.
# We open a structured dataset of type `numpy.ndarray` and serialize it again.

# %%
@task
def to_numpy(ds: Annotated[StructuredDataset, subset_cols]) -> Annotated[StructuredDataset, subset_cols, PARQUET]:
    numpy_array = ds.open(np.ndarray).all()
    return StructuredDataset(dataframe=numpy_array)


# %% [markdown]
# Finally, we define two workflows that showcase how a `pandas.DataFrame` and `FlyteSchema` are accepted by the `StructuredDataset`.
# %%
@workflow
def pandas_compatibility_wf(a: int) -> Annotated[StructuredDataset, subset_cols]:
    df = get_df(a=a)
    ds = get_subset_df(df=df)  # noqa: shown for demonstration; users should use the same types between tasks
    return to_numpy(ds=ds)


@workflow
def schema_compatibility_wf(a: int) -> Annotated[StructuredDataset, subset_cols]:
    df = get_schema_df(a=a)
    ds = get_subset_df(df=df)  # noqa: shown for demonstration; users should use the same types between tasks
    return to_numpy(ds=ds)


# %% [markdown]
# You can run the code locally as follows:
#
# %%
if __name__ == "__main__":
    numpy_array_one = pandas_compatibility_wf(a=42).open(np.ndarray).all()
    print(f"pandas DataFrame compatibility check output: {numpy_array_one}")
    numpy_array_two = schema_compatibility_wf(a=42).open(np.ndarray).all()
    print(f"Schema compatibility check output: {numpy_array_two}")
