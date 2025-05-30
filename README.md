# labelprinter.py

> **An experiment in vibe coding**
>
> *Note from a human:* All code and text in this repo is a result of vibe coding with the Gemini AI, 2025-05-29.
> It took an hour or two, so I'd say that from a developer productivity point of view not worth it.
> The initial version (made in around 5 seconds) was quite good, and making it work manually would probably have taken 10 minutes,
> but making Gemini understand the problems took a lot of time.
> 
> Next day some further vibe coding to add grouping (without cuts)
> 
> The AI had huge problems understanding the cut / no cut behaviour of 
> brother_ql, and also surprisingly with understanding how to code sequential 
> processing and grouping.


# labelprinter.py

**Description:**

This Python script, named `labelprinter.py`, continuously monitors a specified folder for new PNG files. Upon detecting a new PNG file, it adds the file to a queue. A separate worker thread processes the queue, printing each file using the `brother_ql` command-line tool, ensuring labels are printed one at a time. **A grouping option is included: if filenames contain a configurable separator (default "__"), the part of the filename before the first separator is treated as a group. The script includes a short grace period (default 0.25 seconds) to allow for more files belonging to the same group to appear before printing starts for that group. Labels within the same group are printed in the order of their modification time, and the `--no-cut` option is used to prevent cuts between them. A cut will be forced after all files in a group have been printed or when the group changes or the grace period expires.**

The script handles printing success and failure:

* **Successful Printing:** If a PNG file is printed successfully, it is renamed by appending the `.done` suffix to its original name (e.g., `image.png` becomes `image.png.done`).
* **Printing Failure (or Timeout):** If printing fails for any reason (including `brother_ql` errors or exceeding a configurable timeout), the file is renamed by appending the `.error` suffix (e.g., `image.png` becomes `image.png.error`).

The script takes the folder to watch and any necessary parameters for `brother_ql` as command-line arguments, allowing you to specify both global options for `brother_ql` and specific options for its `print` subcommand.

**This program is based on the following prompt given to Gemini. It took quite a bit of "vibe coding" to get the command-line argument parsing for `brother_ql`'s global options and subcommand options working correctly, as `argparse` needed to be carefully configured to separate these different sets of arguments.**

> i want a python program.
> it should continously watch a folder given as command line argument for new png files, ie. files added to the directory after start of the program.
> All new files should be printed using brother\_ql, perhaps spawned in a separate process, as i want this program to survive, not matter what error brother\_ql may experience. If not succesful in printing, after a configurable number of seconds the file should be skipped and the next one processed. skipped files x.png should be renamed to x.png.error, printed ones to x.png.done. Parameters for brother\_ql should also come from the command line

**Usage:**

1.  **Save the script:** Save the Python code as `labelprinter.py`.
2.  **Make the script executable:**

    ```bash
    chmod +x labelprinter.py
    ```
3.  **Create and activate the virtual environment:** This script is designed to run within a virtual environment named `venv` located in the same directory as the script.

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # Or for Windows: .\venv\Scripts\activate
    ```
4.  **Install dependencies:** Ensure you have `watchdog` and `brother_ql` installed *within your activated virtual environment*:

    ```bash
    pip install watchdog brother_ql
    ```
5.  **Run from the command line:** With your virtual environment activated, navigate to the directory of the script and execute it, providing the folder to watch as the first argument, followed by the global `brother_ql` options, the word `print`, and then the `brother_ql print` subcommand options. You can also configure the group separator and grace period.

    ```bash
    ./labelprinter.py ~/spool/cup --printer 10.10.1.18 -m QL-810W -b network print --label 39x48 --600dpi
    ```

    To use a different group separator (e.g., "---") and the default 250ms grace period:

    ```bash
    ./labelprinter.py ~/spool/cup --printer 10.10.1.18 -m QL-810W -b network --group_separator "---" print --label 39x48 --600dpi
    ```

    To specify a different grace period (e.g., 1 second):

    ```bash
    ./labelprinter.py ~/spool/cup --printer 10.10.1.18 -m QL-810W -b network --grace_period 1.0 print --label 39x48 --600dpi
    ```

    You can combine these options as well:

    ```bash
    ./labelprinter.py ~/spool/cup --printer 10.10.1.18 -m QL-810W -b network --group_separator "---" --grace_period 0.5 print --label 39x48 --600dpi
    ```

    * Replace `~/spool/cup` and `10.10.1.18` with your actual folder path and printer address.
    * Other `brother_ql` arguments should be adjusted based on your printer and label requirements.
    * `--group_separator "__"` (or your chosen separator): Specifies the separator used in filenames to identify groups for continuous printing without cuts. Defaults to `"__"`.
    * `--grace_period 0.25` (or your desired time in seconds): Specifies the time to wait for additional files belonging to the same group before printing starts. Defaults to `0.25` seconds.

**Command-Line Arguments:**

* `watch_folder`: (Required) The path to the folder that the script will monitor for new PNG files.
* `--timeout`: (Optional) The number of seconds to wait for the `brother_ql` print command to complete. Defaults to `30` seconds.
* `--error_suffix`: (Optional) The suffix to append to the filename of PNG files that failed to print or timed out. Defaults to `.error`.
* `--done_suffix`: (Optional) The suffix to append to the filename of PNG files that were successfully printed. Defaults to `.done`.
* `--group_separator`: (Optional) The separator string used in filenames to identify groups for continuous printing without cuts. Defaults to `"__"`.
* `--grace_period`: (Optional) The grace period in seconds to wait for new files in the same group. Defaults to `0.25`.
* `brother_ql_args`: (Remaining arguments) Arguments to pass to `brother_ql`. Separate global options from `print` subcommand options by including the word `print` in the arguments.

**Filename Grouping:**

If your filenames follow a pattern like `groupname__uniqueid.png`, where `"__"` is the default `group_separator`, all files with the same `groupname` arriving within the `grace_period` will be printed without an automatic cut in between. A cut will be forced after the grace period expires for a group or when a file with a different `groupname` appears.

**Important Notes:**

* **Virtual Environment:** This script requires a virtual environment named `venv` to be present in the same directory. Ensure you have created and activated it before running the script. The script will check for the existence and activation of this virtual environment.
* This script relies on the `brother_ql` command-line tool being installed and accessible within your activated virtual environment.
* Ensure that your Brother label printer is properly configured and connected to your system.
* The script will only process files that are added to the watched folder *after* the script has started running. Existing PNG files in the folder at the time of startup will not be processed.
* The script now uses a queue and a separate worker thread to ensure that only one instance of `brother_ql` runs at a time.
* The total command passed to `brother_ql` will be printed to the console before attempting to print each file.
* Error messages and status updates will be printed to the console.
* Use `Ctrl+C` in your terminal to stop the script.