# EpiCoV

## Setup

We recommend using a Linux/Unix(Mac) environment. For windows users, we recommend using [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) to create a linux environment. Next, we use a virtual environment, particularly `uv` for ease of handling dependencies. The setup in Linus is as follows:

**Step 1:** Install `uv`

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

**Step 2:** Ensure it is in system `PATH`

```bash
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Step 3:** Create virtual environment and install dependencies

Create a virtual environment named `env_name`. You can find a folder in the same name in your project folder. Next, activate environment and install dependencies from `requirements.txt`

```bash
# Create the virtual environment named <env_name>
uv venv $env_name

# Activate the environment
source $env_name/bin/activate

# Install the dependencies
uv pip install -r requirements.txt
```