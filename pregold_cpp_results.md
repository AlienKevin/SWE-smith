# C++ Pre-Gold Results

## Run Metadata

- Date: 2026-02-18 (PST)
- Scope: all registered C++ profiles
- Timeout policy: pre-gold timeout `500s` per repo (as configured)
- Modal app IDs observed:
  - `ap-ai5ZyYu9iRMdR4bd9rXAQu` (run completion app)
  - `ap-u3EdhJh3mgELuxxGqrLMSw` (app lookup/deployed context used by sandboxes)
- Source log: `pregold_cpp_all.log`

## Exact Command Used

```bash
PYTHONUNBUFFERED=1 stdbuf -oL -eL uv run modal run scripts/pregold_cpp_only_modal.py --max-concurrent-tests 120 2>&1 | tee /Users/kevin/Dev/fall2026/cs329a/SWE-smith-cpp2/pregold_cpp_all.log
```

## Aggregate Summary

- Total repos: **77**
- Pre-gold passed (`ok`): **46**
- Pre-gold failed (`failed`): **31**
- Missing outputs (`missing`): **0**
- Failure reason breakdown:
  - `0 tests passed`: **13**
  - `tests never completed (no end marker)`: **18**

## Failed Repos (31)

- `LibreSprite/LibreSprite`
- `OpenRCT2/OpenRCT2`
- `Qv2ray/Qv2ray`
- `WasmEdge/WasmEdge`
- `WerWolv/ImHex`
- `apache/brpc`
- `aria2/aria2`
- `arvidn/libtorrent`
- `aseprite/aseprite`
- `avast/retdec`
- `azahar-emu/azahar`
- `azerothcore/azerothcore-wotlk`
- `brndnmtthws/conky`
- `diasurgical/DevilutionX`
- `doxygen/doxygen`
- `dragonflydb/dragonfly`
- `duckdb/duckdb`
- `endless-sky/endless-sky`
- `google/highway`
- `halide/Halide`
- `input-leap/input-leap`
- `keepassxreboot/keepassxc`
- `lballabio/QuantLib`
- `libcpr/cpr`
- `mosra/magnum`
- `oatpp/oatpp`
- `opencv/opencv`
- `ossrs/srs`
- `scylladb/seastar`
- `snapcast/snapcast`
- `uxlfoundation/oneTBB`

## Per-Repo Detailed Results

| Repo | Repo ID | Status | Tests Passed | Failure Detail |
|---|---|---|---:|---|
| `Alexays/Waybar` | `Alexays__Waybar.d527ccd4` | `ok` | 7 |  |
| `ArthurSonzogni/FTXUI` | `ArthurSonzogni__FTXUI.f73d92d3` | `ok` | 308 |  |
| `LibreCAD/LibreCAD` | `LibreCAD__LibreCAD.7a288fff` | `ok` | 39 |  |
| `LibreSprite/LibreSprite` | `LibreSprite__LibreSprite.85ced3b6` | `failed` |  | Pre-gold failed: 0 tests passed |
| `Neargye/magic_enum` | `Neargye__magic_enum.c1aa6de9` | `ok` | 15 |  |
| `OpenRCT2/OpenRCT2` | `OpenRCT2__OpenRCT2.f228d738` | `failed` |  | Pre-gold failed: 0 tests passed |
| `OpenTTD/OpenTTD` | `OpenTTD__OpenTTD.ae80a47c` | `ok` | 15 |  |
| `Qv2ray/Qv2ray` | `Qv2ray__Qv2ray.d5c5aeb3` | `failed` |  | Pre-gold failed: 0 tests passed |
| `Tencent/rapidjson` | `Tencent__rapidjson.24b5e7a8` | `ok` | 2 |  |
| `WasmEdge/WasmEdge` | `WasmEdge__WasmEdge.cb41f751` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `WerWolv/ImHex` | `WerWolv__ImHex.f4768420` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `albertlauncher/albert` | `albertlauncher__albert.897c7797` | `ok` | 1 |  |
| `apache/brpc` | `apache__brpc.d22fa17f` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `aria2/aria2` | `aria2__aria2.b4fd7cb1` | `failed` |  | Pre-gold failed: 0 tests passed |
| `aristocratos/btop` | `aristocratos__btop.abcb906c` | `ok` | 1 |  |
| `arvidn/libtorrent` | `arvidn__libtorrent.f0f8a352` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `aseprite/aseprite` | `aseprite__aseprite.da0d3228` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `avast/retdec` | `avast__retdec.8be53bbd` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `azahar-emu/azahar` | `azahar-emu__azahar.37e688f8` | `failed` |  | Pre-gold failed: 0 tests passed |
| `azerothcore/azerothcore-wotlk` | `azerothcore__azerothcore-wotlk.3ffbbe98` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `bblanchon/ArduinoJson` | `bblanchon__ArduinoJson.aa7fbd6c` | `ok` | 27 |  |
| `brndnmtthws/conky` | `brndnmtthws__conky.4f829244` | `failed` |  | Pre-gold failed: 0 tests passed |
| `cuberite/cuberite` | `cuberite__cuberite.7fd3fa5c` | `ok` | 28 |  |
| `danmar/cppcheck` | `danmar__cppcheck.67606e6e` | `ok` | 111 |  |
| `diasurgical/DevilutionX` | `diasurgical__DevilutionX.afdaa2ac` | `failed` |  | Pre-gold failed: 0 tests passed |
| `doctest/doctest` | `doctest__doctest.1da23a3e` | `ok` | 164 |  |
| `doxygen/doxygen` | `doxygen__doxygen.cbd8c4bc` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `dragonflydb/dragonfly` | `dragonflydb__dragonfly.14103bde` | `failed` |  | Pre-gold failed: 0 tests passed |
| `drogonframework/drogon` | `drogonframework__drogon.34955222` | `ok` | 40 |  |
| `duckdb/duckdb` | `duckdb__duckdb.cb9e7c21` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `endless-sky/endless-sky` | `endless-sky__endless-sky.f1dba50f` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `falcosecurity/falco` | `falcosecurity__falco.43aaffc4` | `ok` | 152 |  |
| `gabime/spdlog` | `gabime__spdlog.472945ba` | `ok` | 1 |  |
| `ggerganov/ggwave` | `ggerganov__ggwave.3b877d07` | `ok` | 2 |  |
| `google/benchmark` | `google__benchmark.eed8f5c6` | `ok` | 83 |  |
| `google/bloaty` | `google__bloaty.a277a440` | `ok` | 7 |  |
| `google/draco` | `google__draco.b91aa918` | `ok` | 185 |  |
| `google/glog` | `google__glog.53d58e45` | `ok` | 23 |  |
| `google/googletest` | `google__googletest.5a9c3f9e` | `ok` | 75 |  |
| `google/highway` | `google__highway.224b014b` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `google/leveldb` | `google__leveldb.ac691084` | `ok` | 3 |  |
| `google/sentencepiece` | `google__sentencepiece.0f4ca43a` | `ok` | 1 |  |
| `google/snappy` | `google__snappy.da459b52` | `ok` | 1 |  |
| `gperftools/gperftools` | `gperftools__gperftools.a4724315` | `ok` | 44 |  |
| `grpc/grpc` | `grpc__grpc.9d7a53ea` | `ok` | 15 |  |
| `halide/Halide` | `halide__Halide.c2a6e34e` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `input-leap/input-leap` | `input-leap__input-leap.34a34fb2` | `failed` |  | Pre-gold failed: 0 tests passed |
| `jbeder/yaml-cpp` | `jbeder__yaml-cpp.2e6383d2` | `ok` | 1008 |  |
| `keepassxreboot/keepassxc` | `keepassxreboot__keepassxc.5bd42c47` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `lballabio/QuantLib` | `lballabio__QuantLib.a05b6ab3` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `ledger/ledger` | `ledger__ledger.920059e6` | `ok` | 513 |  |
| `leejet/stable-diffusion.cpp` | `leejet__stable-diffusion.cpp.f0f641a1` | `ok` | 21 |  |
| `leethomason/tinyxml2` | `leethomason__tinyxml2.3324d04d` | `ok` | 1 |  |
| `libcpr/cpr` | `libcpr__cpr.22a41e60` | `failed` |  | Pre-gold failed: 0 tests passed |
| `luanti-org/luanti` | `luanti-org__luanti.fc363085` | `ok` | 9 |  |
| `luau-lang/luau` | `luau-lang__luau.54a2ea00` | `ok` | 4483 |  |
| `microsoft/AirSim` | `microsoft__AirSim.13448700` | `ok` | 1 |  |
| `microsoft/GSL` | `microsoft__GSL.756c91ab` | `ok` | 14 |  |
| `mosra/magnum` | `mosra__magnum.f3a4ce7d` | `failed` |  | Pre-gold failed: 0 tests passed |
| `mumble-voip/mumble` | `mumble-voip__mumble.997ecba9` | `ok` | 15 |  |
| `ninja-build/ninja` | `ninja-build__ninja.cc60300a` | `ok` | 412 |  |
| `oatpp/oatpp` | `oatpp__oatpp.f83d648f` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `open-source-parsers/jsoncpp` | `open-source-parsers__jsoncpp.e799ca05` | `ok` | 3 |  |
| `openMVG/openMVG` | `openMVG__openMVG.c76d8724` | `ok` | 84 |  |
| `opencv/opencv` | `opencv__opencv.aea90a9e` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `ossrs/srs` | `ossrs__srs.6e2392f3` | `failed` |  | Pre-gold failed: 0 tests passed |
| `polybar/polybar` | `polybar__polybar.f99e0b1c` | `ok` | 20 |  |
| `recastnavigation/recastnavigation` | `recastnavigation__recastnavigation.13f43344` | `ok` | 1 |  |
| `scylladb/seastar` | `scylladb__seastar.7e457cf7` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `skypjack/entt` | `skypjack__entt.e08302e1` | `ok` | 13 |  |
| `snapcast/snapcast` | `snapcast__snapcast.439dc886` | `failed` |  | Pre-gold failed: 0 tests passed |
| `sqlitebrowser/sqlitebrowser` | `sqlitebrowser__sqlitebrowser.95f92180` | `ok` | 4 |  |
| `supercollider/supercollider` | `supercollider__supercollider.438bf480` | `ok` | 21 |  |
| `taskflow/taskflow` | `taskflow__taskflow.d8776bc0` | `ok` | 1955 |  |
| `uxlfoundation/oneTBB` | `uxlfoundation__oneTBB.3ebfedd8` | `failed` |  | Pre-gold failed: tests never completed (no end marker) |
| `zaphoyd/websocketpp` | `zaphoyd__websocketpp.4dfe1be7` | `ok` | 1 |  |
| `zeromq/libzmq` | `zeromq__libzmq.51a5a9cb` | `ok` | 119 |  |

## Notes

- All pre-gold outputs were produced after clearing `cpp/bug_gen` and `cpp/run_validation` in Modal volume `swesmith-bug-gen`.
- This run intentionally stopped after pre-gold collection; no post-gold validation was executed in this workflow.
