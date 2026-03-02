# pylint: skip-file

import pandas as pd

from process_van import csv_post_process


def test_csv_post_process_handles_null_name_rows_with_numeric_values():
    input_df = pd.DataFrame(
        {
            "Account Name": ["U.S. stocks & stock funds", "Acct 1", None],
            "Fund Name": [None, "VANGUARD 500 INDEX ADMIRAL CL", None],
            "Symbol": [None, "VFIAX", "Subtotal:"],
            "Value": [None, 4773.99, 243540.99],
            "% of Portfolio": [None, "0.40%", "26.73%"],
        }
    )

    output_df = csv_post_process(input_df)

    assert "Class" in output_df.columns
    assert output_df["Class"].dtype == object
    assert "U.S. stocks & stock funds" in output_df["Class"].values
