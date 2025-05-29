# labelprinter.py

> **An experiment in vibe coding**
>
> *Note from a human:* All code and text in this repo is a result of vibe coding with the Gemini AI, 2025-05-29.
> It took an hour or two, so I'd say that from a developer productivity point of view not worth it.
> The initial version (made in around 5 seconds) was quite good, and making it work manually would probably have taken 10 minutes,
> but making Gemini understand the problems took a lot of time.


**Description:**

This Python script, named `labelprinter.py`, continuously monitors a specified folder for new PNG files. Upon detecting a new PNG file, it adds the file to a queue. A separate worker thread processes the queue, printing each file using the `brother_ql` command-line tool. This design ensures that labels are printed one at a time, preventing multiple instances of `brother_ql` from running concurrently. This design also ensures the main file monitoring thread remains responsive, even if printing takes some time.

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
5.  **Run from the command line:** With your virtual environment activated, navigate to the directory of the script and execute it, providing the folder to watch as the first argument, followed by the global `brother_ql` options, the word `print`, and then the `brother_ql print` subcommand options.

    ```bash
    ./labelprinter.py ~/spool/cup/ --printer /dev/usb/lp0 -m QL-700 -b linux_kernel print --label 39x48 --600dpi
    ```

    * Replace `~/spool/cup/` with the actual path to the directory you want the script to monitor.
    * `--printer /dev/usb/lp0`, `-m QL-700`, `-b linux_kernel`: Example global options for `brother_ql` (e.g., specifying the printer, model, and backend).
    * `print`: The subcommand for printing.
    * `--label 39x48`, `--600dpi`: Example options for the `brother_ql print` subcommand (e.g., specifying the label size and resolution). Refer to the `brother_ql` documentation for available options.

**Command-Line Arguments:**

* `watch_folder`: (Required) The path to the folder that the script will monitor for new PNG files.
* `--timeout`: (Optional) The number of seconds to wait for the `brother_ql` print command to complete. Defaults to `30` seconds.
* `--error_suffix`: (Optional) The suffix to append to the filename of PNG files that failed to print or timed out. Defaults to `.error`.
* `--done_suffix`: (Optional) The suffix to append to the filename of PNG files that were successfully printed. Defaults to `.done`.
* `brother_ql_args`: (Remaining arguments) Arguments to pass to `brother_ql`. Separate global options from `print` subcommand options by including the word `print` in the arguments.

**Important Notes:**

* **Virtual Environment:** This script requires a virtual environment named `venv` to be present in the same directory. Ensure you have created and activated it before running the script. The script will check for the existence and activation of this virtual environment.
* This script relies on the `brother_ql` command-line tool being installed and accessible within your activated virtual environment.
* Ensure that your Brother label printer is properly configured and connected to your system.
* The script will only process files that are added to the watched folder *after* the script has started running. Existing PNG files in the folder at the time of startup will not be processed.
* The script now uses a queue and a separate worker thread to ensure that only one instance of `brother_ql` runs at a time.
* The total command passed to `brother_ql` will be printed to the console before attempting to print each file.
* Error messages and status updates will be printed to the console.
* Use `Ctrl+C` in your terminal to stop the script.