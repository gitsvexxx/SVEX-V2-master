## Set Up

1.  **Install `uv`**
    *   If you don't have `uv` installed, run one of the following commands:

    *   **macOS / Linux:**
        ```sh
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```
    *   **Windows (Powershell):**
        ```powershell
        irm https://astral.sh/uv/install.ps1 | iwr
        ```

2.  **Clone the Project**
    *   Clone this repository to your local machine.
    *   Navigate into the project directory: `cd SVEX_Project`

3.  **Create Environment & Install Dependencies**
    *   Create a virtual environment and sync it with the project's dependencies in one step. `uv` will automatically find the dependencies in your `pyproject.toml` file.
        ```sh
        uv sync
        ```
    *   This command creates a `.venv` directory if it doesn't exist and installs the exact dependencies specified for the project.

4.  **Set Up the Database**
    *   Make and apply the database migrations. We use `uv run` to execute commands within the managed environment.
        ```sh
        uv run python manage.py makemigrations
        uv run python manage.py migrate
        ```

5.  **Create an Admin/Superuser**
    *   Create an administrator account to access the Django admin panel:
        ```sh
        uv run python manage.py createsuperuser
        ```

6.  **Run the Development Server**
    *   First, check for any project issues:
        ```sh
        uv run python manage.py check
        ```
    *   Then, start the development server:
        ```sh
        uv run python manage.py runserver
        ```
    *   The application will be available at `http://127.0.0.1:8000/`.

## Common Commands

All commands are executed using `uv run` to ensure they use the project's virtual environment and dependencies.

*   **Run the server:**
    ```sh
    uv run python manage.py runserver
    ```
*   **Create database migrations:**
    ```sh
    uv run python manage.py makemigrations
    ```
*   **Apply database migrations:**
    ```sh
    uv run python manage.py migrate
    ```
*   **Check project health:**
    ```sh
    uv run python manage.py check
    ```
*   **Format code with Black:**
    ```sh
    uv run black .
    ```
*   **Django template tag for static files:**
    *(For use inside Django HTML templates)*
    ```django
    {% load static %}
    ```
