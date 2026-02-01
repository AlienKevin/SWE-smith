import re

from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.constants import ENV_NAME
from swesmith.profiles.base import RepoProfile, registry


DEFAULT_CPP_BUG_GEN_DIRS_EXCLUDE = [
    # Docs / metadata.
    "/doc",
    "/docs",
    # Examples / benchmarks are typically not covered by ctest.
    "/bench",
    "/benchmark",
    "/example",
    "/examples",
    # Build / tooling.
    "/cmake",
    "/scripts",
    "/tools",
]


@dataclass
class CppProfile(RepoProfile):
    """
    Profile for C++ repositories.
    """

    exts: list[str] = field(
        default_factory=lambda: [".cpp", ".cc", ".cxx", ".h", ".hpp"]
    )
    # Exclude directories that are typically not built/executed by unit tests.
    bug_gen_dirs_exclude: list[str] = field(
        default_factory=lambda: list(DEFAULT_CPP_BUG_GEN_DIRS_EXCLUDE)
    )

    def extract_entities(
        self,
        dirs_exclude: list[str] | None = None,
        dirs_include: list[str] = [],
        exclude_tests: bool = True,
        max_entities: int = -1,
    ) -> list:
        if dirs_exclude is None:
            dirs_exclude = []
        merged_excludes = [*dirs_exclude, *self.bug_gen_dirs_exclude]
        return super().extract_entities(
            dirs_exclude=merged_excludes,
            dirs_include=dirs_include,
            exclude_tests=exclude_tests,
            max_entities=max_entities,
        )


@dataclass
class Catch29b3f508a(CppProfile):
    owner: str = "catchorg"
    repo: str = "Catch2"
    commit: str = "9b3f508a1b1579f5366cf83d19822cb395f23528"
    test_cmd: str = (
        "cd build && cmake --build . -j$(nproc) && ctest --output-on-failure --verbose"
    )
    timeout: int = 300  # 5 minutes - allows time for incremental rebuild + 71 tests
    # Exclude directories not used in cmake build or not covered by tests
    bug_gen_dirs_exclude: list[str] = field(
        default_factory=lambda: [
            *DEFAULT_CPP_BUG_GEN_DIRS_EXCLUDE,
            "/extras",  # Amalgamated single-file version (not used in cmake build)
            "/third_party",  # Bundled third-party libraries (not tested)
            "/fuzzing",  # Fuzzing harness code (not library code)
        ]
    )

    @property
    def dockerfile(self):
        return f"""FROM gcc:12
RUN apt-get update && apt-get install -y \
    libbrotli-dev libcurl4-openssl-dev \
    clang build-essential cmake \
    python3 python3-dev python3-pip

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mkdir build && cd build \
    && cmake .. -DCATCH_DEVELOPMENT_BUILD=ON \
    && make all \
    && ctest"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        re_passes = [
            re.compile(r"^-- Performing Test (.+) - Success$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\s+ Passed\s+.+$", re.IGNORECASE
            ),
        ]
        re_fails = [
            re.compile(r"^-- Performing Test (.+) - Failed$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\*\*\*Failed\s+.+$", re.IGNORECASE
            ),
        ]
        re_skips = [
            re.compile(r"^-- Performing Test (.+) - skipped$", re.IGNORECASE),
        ]

        for line in log.splitlines():
            line = line.strip().lower()
            if not line:
                continue

            for re_pass in re_passes:
                pass_match = re_pass.match(line)
                if pass_match:
                    test = pass_match.group(1)
                    test_status_map[test] = TestStatus.PASSED.value

            for re_fail in re_fails:
                fail_match = re_fail.match(line)
                if fail_match:
                    test = fail_match.group(1)
                    test_status_map[test] = TestStatus.FAILED.value

            for re_skip in re_skips:
                skip_match = re_skip.match(line)
                if skip_match:
                    test = skip_match.group(1)
                    test_status_map[test] = TestStatus.SKIPPED.value

        return test_status_map


@dataclass
class Spdlog8806ca65(CppProfile):
    owner: str = "gabime"
    repo: str = "spdlog"
    commit: str = "8806ca6509f037cf7612ea292338e3b222209dc1"
    test_cmd: str = (
        "cd build && cmake --build . -j$(nproc) && ctest --output-on-failure --verbose"
    )
    timeout: int = 300
    org_dh: str = "zhehaoli1999"  # Docker Hub username
    org_gh: str = "zhehaoli1999"  # GitHub username (for personal account)
    # Exclude bundled fmt library - spdlog's tests don't cover fmt internals,
    # causing ~70% of bugs in bundled/fmt to pass tests (only 3.2% validation rate)
    bug_gen_dirs_exclude: list[str] = field(
        default_factory=lambda: [
            *DEFAULT_CPP_BUG_GEN_DIRS_EXCLUDE,
            "/include/spdlog/fmt/bundled",
        ]
    )

    @property
    def dockerfile(self):
        # DEBUG: Print the full mirror URL
        mirror_url = f"https://github.com/{self.mirror_name}"
        print(f"[DEBUG] Mirror URL: {mirror_url}")
        print(f"[DEBUG] Mirror name: {self.mirror_name}")
        print(f"[DEBUG] Repo name: {self.repo_name}")
        print(f"[DEBUG] Org GH: {self.org_gh}")

        return f"""FROM gcc:12
RUN apt-get update && apt-get install -y \
    clang build-essential cmake \
    python3 python3-dev python3-pip

# Clone the mirror repository to /testbed
RUN git clone {mirror_url} /testbed
WORKDIR /testbed

# Build and test spdlog
RUN mkdir build && cd build \
    && cmake .. -DSPDLOG_BUILD_TESTS=ON \
    && cmake --build . -j$(nproc) \
    && ctest --output-on-failure --verbose"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        re_passes = [
            re.compile(r"^-- Performing Test (.+) - Success$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\s+ Passed\s+.+$", re.IGNORECASE
            ),
        ]
        re_fails = [
            re.compile(r"^-- Performing Test (.+) - Failed$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\*\*\*Failed\s+.+$", re.IGNORECASE
            ),
        ]
        re_skips = [
            re.compile(r"^-- Performing Test (.+) - skipped$", re.IGNORECASE),
        ]

        for line in log.splitlines():
            line = line.strip().lower()
            if not line:
                continue

            for re_pass in re_passes:
                pass_match = re_pass.match(line)
                if pass_match:
                    test = pass_match.group(1)
                    test_status_map[test] = TestStatus.PASSED.value

            for re_fail in re_fails:
                fail_match = re_fail.match(line)
                if fail_match:
                    test = fail_match.group(1)
                    test_status_map[test] = TestStatus.FAILED.value

            for re_skip in re_skips:
                skip_match = re_skip.match(line)
                if skip_match:
                    test = skip_match.group(1)
                    test_status_map[test] = TestStatus.SKIPPED.value

        return test_status_map


@dataclass
class Eigen9b00db8c(CppProfile):
    owner: str = "libeigen"
    repo: str = "eigen"
    commit: str = "9b00db8cb9154477b93b342cf418b5da5d7f58a0"
    # Exclude directories that are mostly not built/covered by the default test suite.
    bug_gen_dirs_exclude: list[str] = field(
        default_factory=lambda: [
            *DEFAULT_CPP_BUG_GEN_DIRS_EXCLUDE,
            "/unsupported",
            "/blas",
            "/Eigen/src/Core/arch",
        ]
    )
    test_cmd: str = "cd build && cmake --build . -j$(nproc) && ctest --output-on-failure --continue-on-failure --timeout 3600 --verbose"
    timeout: int = (
        1800  # 30 minutes - Eigen test suite is large and can take a long time
    )
    timeout_ref: int = 3600  # 60 minutes for reference runs
    org_dh: str = "zhehaoli1999"  # Docker Hub username
    org_gh: str = "zhehaoli1999"  # GitHub username (for personal account)

    @property
    def dockerfile(self):
        # DEBUG: Print the full mirror URL
        mirror_url = f"https://github.com/{self.mirror_name}"
        print(f"[DEBUG] Mirror URL: {mirror_url}")
        print(f"[DEBUG] Mirror name: {self.mirror_name}")
        print(f"[DEBUG] Repo name: {self.repo_name}")
        print(f"[DEBUG] Org GH: {self.org_gh}")

        return f"""FROM gcc:12
RUN apt-get update && apt-get install -y \
    git clang build-essential cmake \
    python3 python3-dev python3-pip

# Clone the mirror repository to /testbed
RUN git clone https://gitlab.com/libeigen/eigen.git /testbed \
    && cd /testbed \
    && git checkout 9b00db8cb9154477b93b342cf418b5da5d7f58a0
WORKDIR /testbed


# Build and test spdlog
RUN mkdir build && cd build \
    && cmake .. -DBUILD_TESTING=ON \
    && cmake --build . -j$(nproc)
    
RUN cd build && ctest --output-on-failure --continue-on-failure --timeout 36000 --verbose || true
    """

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        re_passes = [
            re.compile(r"^-- Performing Test (.+) - Success$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\s+ Passed\s+.+$", re.IGNORECASE
            ),
        ]
        re_fails = [
            re.compile(r"^-- Performing Test (.+) - Failed$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\*\*\*Failed\s+.+$", re.IGNORECASE
            ),
        ]
        re_skips = [
            re.compile(r"^-- Performing Test (.+) - skipped$", re.IGNORECASE),
        ]

        for line in log.splitlines():
            line = line.strip().lower()
            if not line:
                continue

            for re_pass in re_passes:
                pass_match = re_pass.match(line)
                if pass_match:
                    test = pass_match.group(1)
                    test_status_map[test] = TestStatus.PASSED.value

            for re_fail in re_fails:
                fail_match = re_fail.match(line)
                if fail_match:
                    test = fail_match.group(1)
                    test_status_map[test] = TestStatus.FAILED.value

            for re_skip in re_skips:
                skip_match = re_skip.match(line)
                if skip_match:
                    test = skip_match.group(1)
                    test_status_map[test] = TestStatus.SKIPPED.value

        return test_status_map


@dataclass
class FmtEc73fb72(CppProfile):
    owner: str = "fmtlib"
    repo: str = "fmt"
    commit: str = "ec73fb72"
    test_cmd: str = "cd build && cmake --build . -j$(nproc) && ctest --output-on-failure --continue-on-failure --timeout 3600 --verbose"
    timeout: int = 600  # 10 minutes - fmt test suite is smaller than Eigen
    timeout_ref: int = 1200  # 20 minutes for reference runs
    org_dh: str = "zhehaoli1999"  # Docker Hub username
    org_gh: str = "cs329a-swesmith-repos"  # GitHub username (for personal account)

    @property
    def dockerfile(self):
        # DEBUG: Print the full mirror URL
        mirror_url = f"https://github.com/{self.mirror_name}"
        print(f"[DEBUG] Mirror URL: {mirror_url}")
        print(f"[DEBUG] Mirror name: {self.mirror_name}")
        print(f"[DEBUG] Repo name: {self.repo_name}")
        print(f"[DEBUG] Org GH: {self.org_gh}")

        return f"""FROM gcc:12
RUN apt-get update && apt-get install -y \
    git clang build-essential cmake \
    python3 python3-dev python3-pip

# Clone the mirror repository to /testbed
RUN git clone {mirror_url} /testbed \
    && cd /testbed \
    && git checkout {self.commit}
WORKDIR /testbed

# Build and test fmt
# FMT_TEST enables the test target (enabled by default when fmt is the master project)
RUN mkdir build && cd build \
    && cmake .. -DFMT_TEST=ON \
    && cmake --build . -j$(nproc)
    
RUN cd build && ctest --output-on-failure --continue-on-failure --timeout 3600 --verbose || true
    """

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        re_passes = [
            re.compile(r"^-- Performing Test (.+) - Success$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\s+ Passed\s+.+$", re.IGNORECASE
            ),
        ]
        re_fails = [
            re.compile(r"^-- Performing Test (.+) - Failed$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\*\*\*Failed\s+.+$", re.IGNORECASE
            ),
        ]
        re_skips = [
            re.compile(r"^-- Performing Test (.+) - skipped$", re.IGNORECASE),
        ]

        for line in log.splitlines():
            line = line.strip().lower()
            if not line:
                continue

            for re_pass in re_passes:
                pass_match = re_pass.match(line)
                if pass_match:
                    test = pass_match.group(1)
                    test_status_map[test] = TestStatus.PASSED.value

            for re_fail in re_fails:
                fail_match = re_fail.match(line)
                if fail_match:
                    test = fail_match.group(1)
                    test_status_map[test] = TestStatus.FAILED.value

            for re_skip in re_skips:
                skip_match = re_skip.match(line)
                if skip_match:
                    test = skip_match.group(1)
                    test_status_map[test] = TestStatus.SKIPPED.value

        return test_status_map


# Register all C++ profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, CppProfile)
        and obj.__name__ != "CppProfile"
    ):
        # NOTE: Skipping eigen as it times out during pre-gold (over 500s)
        if obj.__name__ in ["Eigen9b00db8c"]:
            continue
        registry.register_profile(obj)
