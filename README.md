### 用途

- 修改任意次提交的作者、时间及提交描述

- 批量按照指定的作者、时间线 随机调整作者、时间

- 支持强推修改到远程仓库

  > 依赖本地的git用户权限
  
  

### 前置条件：

- 本地需要安装python 并配置了环境变量

  > 不低于python3.8

- 本地安装了Git

- 安装git-filter-repo

  > [git-filter-repo](https://github.com/newren/git-filter-repo)

  

### 打包

- 安装依赖包

  ```shell
  pip install -r .\requirements.txt
  ```

- 打exe包

  ```shell
  pip install pyinstaller 
  python.exe -m PyInstaller -F main.py  --noconsole
  ```

### 配置用户

- 在exe包的同目录下增加`config.json`

  ```json
  {
    "authors": [
      "zhangsan <zhangsan@XXx.com>",
      "lisi <lisi@XXx.com>",
      "wangwu <wangwu@XXx.com>",
      "zhaoliu <zhaoliu@XXx.com>"
    ]
  }
  ```
  
> authors  用于指定作者列表