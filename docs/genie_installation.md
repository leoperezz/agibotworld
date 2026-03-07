# Genie Sim — Docker Installation Tutorial

This guide walks you through installing and running **Genie Sim** using the recommended **Docker** setup.

---

## 1. Requirements

### 1.1 Software

| Item | Minimum | Tested |
|------|---------|--------|
| OS | Ubuntu 22.04 / 24.04 | Ubuntu 22.04 |
| Simulator | NVIDIA Isaac Sim 5.1.0 | NVIDIA Isaac Sim 5.1.0 |

Official Isaac Sim requirements: [Installation & Requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)

### 1.2 Hardware (Minimum)

- **CPU:** Intel Core i7 (7th Gen) or AMD Ryzen 5  
- **RAM:** 32 GB  
- **GPU:** GeForce RTX 4080  
- **Driver:** 580.65.06  
- **Storage:** 50 GB SSD  

### 1.3 Hardware (Tested)

- **CPU:** Intel Core i7 (12th Gen)  
- **RAM:** 64 GB  
- **GPU:** GeForce RTX 4090D  
- **Driver:** 550.120 + CUDA 12.4  
- **Storage:** 1 TB NVMe SSD  

### 1.4 Docker

- Install Docker according to the **Isaac Sim documentation** so that Isaac Sim runs correctly inside containers.

---

## 2. Download

### 2.1 Genie Sim Repository

Clone the Genie Sim repo:

```bash
git clone https://github.com/AgibotTech/genie_sim.git
cd genie_sim
```

### 2.2 Genie Sim Assets

1. Open: **https://modelscope.cn/datasets/agibot_world/GenieSimAssets**  
2. Follow the page instructions to download the **Genie Sim Assets**.  
3. Place the downloaded assets in:

   ```text
   genie_sim/source/geniesim/assets
   ```

> **Note:** Assets may also be published on Hugging Face in the future.

---

## 3. Docker Installation (Recommended)

### 3.1 Build the Docker Image

From the **Genie Sim** repository root:

```bash
cd genie_sim
docker build -f ./scripts/dockerfile -t registry.agibot.com/genie-sim/open_source:latest .
```

> **Note:** Genie Sim Benchmark dropped support for Curobo since version 3.0.

### 3.2 Start the GUI Container

Ensure **GenieSimAssets** are in `genie_sim/source/geniesim/assets`, then start the container:

```bash
cd genie_sim
./scripts/start_gui.sh
```

### 3.3 Enter the Container

In a **new terminal**, from the same repo root:

```bash
cd genie_sim
./scripts/into.sh
```

### 3.4 Run the Demo

Inside the container:

```bash
/geniesim/main$ omni_python source/geniesim/app/app.py --config ./source/geniesim/config/select_color.yml
```

You should see the Genie Sim demo running with the selected config.

---

## 4. Summary Checklist

- [ ] Ubuntu 22.04/24.04 with required hardware (GPU, RAM, storage)  
- [ ] Docker installed (per Isaac Sim docs)  
- [ ] `genie_sim` repo cloned  
- [ ] Genie Sim Assets downloaded and placed in `genie_sim/source/geniesim/assets`  
- [ ] Docker image built with the provided Dockerfile  
- [ ] Container started with `./scripts/start_gui.sh`  
- [ ] Second terminal: entered container with `./scripts/into.sh`  
- [ ] Demo run with `omni_python source/geniesim/app/app.py --config ./source/geniesim/config/select_color.yml`  

---

## 5. Optional: Use Genie Sim as a Python Module

If you need to **import** `geniesim` from another workspace (tested with **Conda Python 3.11**):

```bash
cd genie_sim
conda create --name geniesim python=3.11
conda activate geniesim
python -m pip install -e ./source
```

> Use this only when you need Genie Sim as a library; for running the sim and demos, the Docker flow above is recommended.

---

## 6. Optional: Pre-commit Hooks (Developers)

To enable automatic formatting (Python, JSON, YAML, etc.) on commit:

1. Install dependencies from `requirements.txt` in your environment.  
2. Install and enable pre-commit:

```bash
cd genie_sim
pip install pre-commit
pre-commit install
```

3. Format all tracked files once:

```bash
pre-commit run --all-files
```

Pre-commit will run automatically on `git commit` when enabled.

---

## 7. Host Installation (Not Recommended)

We **strongly recommend** the Docker setup above. If you must use the host machine:

- **Docker users:** Install the same dependencies listed in the provided **Dockerfile**.  
- **Conda users:** Follow the “Use Genie Sim as Python Module” section and match the environment used there.

---

For more details, see the [Genie Sim repository](https://github.com/AgibotTech/genie_sim) and the [Genie Sim Assets](https://modelscope.cn/datasets/agibot_world/GenieSimAssets) page.
