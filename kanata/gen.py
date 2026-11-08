#!/usr/bin/env python3
"""生成 ~/.config/kanata/macos-emacs.kbd。

为什么用生成器：每个 layer 都要给 defsrc 里所有键一个条目（没改写的键要继续带
原修饰键，比如按住 CapsLock 时 caps+t 仍要是 Ctrl+t），手写容易漏、改一处要动
好几层。表在上、输出在下，改表后重新生成即可。

用法：
  python3 ~/.config/kanata/gen.py > ~/.config/kanata/macos-emacs.kbd
  kanata --check --cfg ~/.config/kanata/macos-emacs.kbd
"""

# ---------------------------------------------------------------------------
# 表
# ---------------------------------------------------------------------------

# defsrc：字母+数字+标点+导航键，外加 5 个修饰键（顺序与每层条目一一对应）
LETTERS = list("qwertyuiopasdfghjklzxcvbnm")
DIGITS = list("1234567890")
PUNCT = ["-", "=", "[", "]", ";", "'", ",", ".", "/", "\\", "`"]
NAV = ["tab", "ret", "spc", "bspc", "del", "up", "down", "left", "right", "home", "end", "pgup", "pgdn"]
PLAIN_KEYS = LETTERS + DIGITS + PUNCT + NAV

MOD_KEYS = ["caps", "lalt", "lctl", "esc", "ralt"]

# xremap Global-Emacs-like（只排除终端，IDE 里也生效）
EMACS_R1 = {
    "b": "left",
    "f": "right",
    "p": "up",
    "n": "down",
    "a": "home",
    "e": "end",
}
ALT_R1 = {
    "b": "(multi lctl left)",
    "f": "(multi lctl right)",
    "v": "pgup",
    ",": "(multi lctl home)",   # M-Shift-, -> Ctrl+Home（无法区分 Shift，见文件末尾说明）
    ".": "(multi lctl end)",    # M-Shift-. -> Ctrl+End
}

# xremap Emacs-not-in-ide（终端和 IDE 都排除）
EMACS_R2 = {
    "m": "ret",
    "j": "ret",
    "o": "(macro ret left)",
    "w": "(multi lctl x)",      # 剪切
    "y": "(multi lctl v)",      # 粘贴
    "d": "del",
    "h": "bspc",
    "k": "(macro S-end C-x)",  # 行末选区后剪切（Shift+End 选中到行尾，Ctrl+X 剪切）
    "s": "(multi lctl f)",      # 搜索
    "r": "(multi lsft f3)",
    "/": "(multi lctl z)",      # 撤销
}
ALT_R2 = {
    "w": "(multi lctl c)",      # 复制
    "d": "(multi lctl del)",
    "bspc": "(multi lctl bspc)",  # Alt-backspace -> Ctrl+Backspace
}

# mark 模式（xremap 的 set_mark/with_mark）：Ctrl+Alt+Space 开关
# 注意：kanata 的 macro 里不能写 multi/layer 动作，所以这里只用切换层，
# 不再额外输出 C-Shift-right；xremap 的「操作后自动收回 mark」也没做（见文件末尾说明）。
MARK_CHORD = "(layer-toggle emacs-mark)"

# 物理左 Alt 按住时持续输出左 Ctrl，让鼠标单击、滚轮及 defsrc 外的键也能带 Ctrl。
# c/v 用 unmod 临时抑制左 Ctrl，松开 c/v 后自动恢复；不能用 release-key 永久释放。
META_HOLD = "(multi lctl (layer-while-held meta))"
# 这几个键进 defsrc 只为让 switch 的 (input real ...) 能读到它们——kanata 看不见没进 defsrc 的
# 键是否被按住；各层里它们原样透传，所以行为不变。
PASS_KEYS = ["lmet", "rmet", "lsft", "rsft"]


def meta_chord(key, guard_super):
    """meta 层 c/v：物理 Shift（v 还包括物理 Super）也按住时不抢键，发带 Ctrl 的键——
    Ctrl+Shift+C/V、以及 Super+Ctrl+V（剪贴板历史）；都没按住才发 Super+C/V，交给 omarchy 的
    Universal copy/paste（当前 Omarchy：非终端 Ctrl+C/V，终端 Ctrl+Shift+C/V）。

    坑：switch 的 triple 是三条并列项，不能再包一层括号（(() (multi ...) break) 会报
    "switch expects triples of params"）。
    """
    checks = ["(input real lsft)", "(input real rsft)"]
    if guard_super:
        checks = ["(input real lmet)", "(input real rmet)"] + checks
    return (f"(switch ({' '.join(checks)}) (multi lctl {key}) break "
            f"() (unmod (lctl) lmet {key}) break)")


META_REMAP = {
    # c 不用看 Super：⌘+Super+C 直接给 Super+C（就是复制）
    "c": meta_chord("c", guard_super=False),
    # v 要看 Super：⌘+Super+V 得发 Ctrl+V，才配得上 SUPER+CTRL+V（剪贴板历史）
    "v": meta_chord("v", guard_super=True),
}

# IDE（editor 层）按住物理 Alt（= ⌘）：w 发 vim 式 chord（先 Ctrl+W 再 C），其余键同 meta。
# 80ms 让编辑器认出 ctrl-w 前缀（vim 插件的窗口前缀要等下一个键；(macro ...) 不因释放取消）
META_EDITOR_REMAP = dict(META_REMAP)
META_EDITOR_REMAP["w"] = "(macro C-w 80 (unmod (lctl) c))"

HEADER = """\
;; macOS 风格修饰键 + Emacs 编辑键 —— xremap config.yaml 的 kanata 版
;; 本文件由 ~/.config/kanata/gen.py 生成，不要手改（改 gen.py 后重新生成）。
;;
;; 物理键 ↔ 输出（xremap 的 modmap macos-like）：
;;   CapsLock  按住 -> 右 Ctrl（terminal）或 emacs 层（base/editor/zed）
;;             单击 -> Esc
;;   Alt_L     -> 左 Ctrl（macOS 的 ⌘ 位）；按住它还会进 meta 层（editor 里进 meta-editor，见下）
;;   Ctrl_L    -> Alt（macOS 的 ⌥ 位）；按住它还会进 alt 层（见下）
;;   Esc       -> `        Alt_R -> Left
;;
;; base layer 由 ~/.local/bin/kanata-window-layer 按当前窗口/浮层切换：
;;   base           默认；omarchy menu / snippets 面板也走这里
;;   terminal       kitty / alacritty —— 终端里两条 Emacs 规则都不生效
;;   editor         jetbrains-* / Code / Windsurf —— 只有规则一（Ctrl_R-b/f/p/n/a/e、M-*）生效，
;;                  规则二（Ctrl_R-w/y/m/j/k…）刻意不生效：那是 IDE 自己的 Ctrl+W/Ctrl+K 等
;;   zed            同 editor；物理左 Alt+C/V 输出 Ctrl+Shift+C/V，编辑器和终端统一复制粘贴
;;
;; 派生层（由上面几层按住修饰键进入）：
;;   emacs / emacs-editor   按住 CapsLock；未改写的键继续带右 Ctrl（caps+t 还是 Ctrl+t）
;;   alt / alt-editor       按住物理 Ctrl（= Alt）；未改写的键继续带 Alt（Alt+Tab 照旧）
;;   meta-editor            只在 editor 层出现（代替 meta）：同 meta，但 w 发宏「Ctrl+W 然后 C」
;;   emacs-mark             Ctrl+Alt+Space 开关；b/f/p/n 变成 Shift+方向（选区）
;;   meta                   按住物理 Alt（= ⌘）；c/v 发 Super+C/V 交给 omarchy 的
;;                          Universal copy/paste（当前 Omarchy：非终端 Ctrl+C/V，
;;                          终端 Ctrl+Shift+C/V）；另按 Shift 或在 v 上另按物理 Super 时：
;;                          ⌘+Shift+C/V 是 Ctrl+Shift+C/V，⌘+Super+V 是剪贴板历史；
;;                          持续保持左 Ctrl，支持 ⌘+单击/滚轮；c/v 结束后恢复左 Ctrl
;;
;; 只有 defsrc 里的键会被接管，其余键原样通过（process-unmapped-keys no）。
;; defsrc 末尾的 lmet/rmet/lsft/rsft 只为让层里的 (input real ...) 能读到它们，各层原样透传。
"""


def mods_for(name, lctl_action, lalt_action):
    """5 个修饰键在某一层的条目。lctl_action/lalt_action 可覆盖。"""
    return {
        "caps": None,  # 由每层显式给
        "lalt": lalt_action,
        "lctl": lctl_action,
        "esc": "grv",
        "ralt": "left",
    }


def layer(name, caps_action, key_remap=None, mod_prefix=None, lctl=None, lalt=None):
    """生成一个 (deflayer ...)。

    key_remap  : {key: action}，覆盖该键
    mod_prefix : 未覆盖的键统一输出 (multi <前缀> <键>)，用于「保持原修饰键」
    lctl/lalt  : 覆盖物理 Ctrl_L / Alt_L 的输出（默认走 modmap：lctl->lalt, lalt->lctl）
    """
    key_remap = key_remap or {}
    lctl_action = lctl if lctl else "lalt"
    lalt_action = lalt if lalt else "lctl"
    lines = [f"(deflayer {name}"]
    lines.append(f"  {caps_action}")
    lines.append(f"  {lalt_action}")
    lines.append(f"  {lctl_action}")
    lines.append("  grv")
    lines.append("  left")
    for key in PLAIN_KEYS:
        if key in key_remap:
            lines.append(f"  {key_remap[key]}")
        elif mod_prefix:
            lines.append(f"  (multi {mod_prefix} {key})")
        else:
            lines.append(f"  {key}")
    for key in PASS_KEYS:
        lines.append(f"  {key}")  # 物理 Super / Shift 原样透传
    lines.append(")")
    return "\n".join(lines)


def emacs_layer(name, lctl_action, extra=None):
    """emacs 层：规则一的键 + extra（规则二，只给 base 用）；其余键带右 Ctrl。"""
    remap = dict(EMACS_R1)
    if extra:
        remap.update(extra)
    return layer(name, "(tap-hold-press 200 200 esc rctl)", key_remap=remap,
                 mod_prefix="rctl", lctl=lctl_action, lalt=META_HOLD)


def alt_layer(name, extra=None):
    """alt 层：规则一的 M-* + extra（规则二的 M-*，只给 base 用）；其余键带 Alt。"""
    remap = dict(ALT_R1)
    if extra:
        remap.update(extra)
    return layer(name, "(tap-hold-press 200 200 esc ralt)", key_remap=remap,
                 mod_prefix="lalt", lctl="lalt", lalt=META_HOLD)


def mark_layer(name):
    """mark 层：= emacs 层，但 b/f/p/n 变成 Shift+方向；触发重置的键额外关掉本层。"""
    remap = dict(EMACS_R1)
    remap.update(EMACS_R2)
    shift_arrows = {"b": "(multi lsft left)", "f": "(multi lsft right)",
                    "p": "(multi lsft up)", "n": "(multi lsft down)"}
    remap.update(shift_arrows)
    remap["spc"] = MARK_CHORD  # 再按一次收回 mark
    return layer(name, "(tap-hold-press 200 200 esc rctl)", key_remap=remap,
                 mod_prefix="rctl", lctl="(layer-while-held alt)", lalt=META_HOLD)



RCFG = """(defcfg
  process-unmapped-keys no
  linux-dev ( /dev/input/by-id/usb-winkeyless.kr_ps2avrGB-event-kbd /dev/input/by-id/usb-XCTECH_Wireless_Receiver-if01-event-kbd )
)
""".rstrip("\n")
def main():
    print(HEADER)
    # linux-dev：只抓键盘节点。kanata 不写这项时默认抓 /dev/input/by-id/* 下的
    # 全部设备，连鼠标也独占（EVIOCGRAB）；那会让 OpenLogi 的 evdev hook 抓不到
    # 鼠标，Back/Forward 的四向手势失效（hook 报 Device or resource busy）。
    print(RCFG)
    print()
    print("(defsrc")
    print("  " + "  ".join(MOD_KEYS + PLAIN_KEYS + PASS_KEYS))
    print(")")
    print()
    print(";; base：CapsLock 进 emacs 层，物理 Ctrl 进 alt 层，物理 Alt 进 meta 层")
    print(layer("base", "(tap-hold-press 200 200 esc (layer-while-held emacs))",
                lctl="(layer-while-held alt)", lalt=META_HOLD))
    print()
    print(";; terminal：两条 Emacs 规则都不生效，修饰键只剩 modmap 本身 + meta")
    print(layer("terminal", "(tap-hold-press 200 200 esc rctl)", lalt=META_HOLD))
    print()
    print(";; editor：只有规则一（IDE 里 Ctrl+W/Ctrl+K 等要留给 IDE 自己）")
    print(layer("editor", "(tap-hold-press 200 200 esc (layer-while-held emacs-editor))",
                lctl="(layer-while-held alt-editor)", lalt="(multi lctl (layer-while-held meta-editor))"))
    print()
    print(";; Zed：右 Ctrl 的 Emacs 规则同 editor；左 Alt+C/V 专用复制粘贴")
    print(layer("zed", "(tap-hold-press 200 200 esc (layer-while-held emacs-editor))",
                lctl="(layer-while-held alt-editor)", lalt="(multi lctl (layer-while-held meta-zed))"))
    print()
    print(";; meta：按住物理 Alt（⌘ 位）；c/v 例外，其余键逐键带 Ctrl")
    print(layer("meta", "(tap-hold-press 200 200 esc rctl)", key_remap=META_REMAP,
                mod_prefix="lctl"))
    print()
    print(";; meta-editor：同 meta，但 w 发 chord（Ctrl+W 然后 C）——只给 editor 层用")
    print(layer("meta-editor", "(tap-hold-press 200 200 esc rctl)",
                key_remap=META_EDITOR_REMAP, mod_prefix="lctl"))
    print()
    print(";; Zed 编辑器与终端都用 Ctrl+Shift+C/V；右 Ctrl+C 不经过本层")
    print(layer("meta-zed", "(tap-hold-press 200 200 esc rctl)",
                key_remap={**META_EDITOR_REMAP, "c": "(multi lctl lsft c)",
                           "v": "(multi lctl lsft v)"}, mod_prefix="lctl"))
    print(";; emacs：按住 CapsLock；规则一 + 规则二")
    print(emacs_layer("emacs", "(layer-while-held alt)", extra=EMACS_R2))
    print()
    print(";; emacs-editor：按住 CapsLock；只有规则一")
    print(emacs_layer("emacs-editor", "(layer-while-held alt-editor)"))
    print()
    print(";; alt：按住物理 Ctrl（= Alt）；规则一 + 规则二，Alt+Space 开 mark")
    alt_extra = dict(ALT_R2)
    alt_extra["spc"] = MARK_CHORD
    print(alt_layer("alt", extra=alt_extra))
    print()
    print(";; alt-editor：按住物理 Ctrl；只有规则一")
    print(alt_layer("alt-editor"))
    print()
    print(";; emacs-mark：Ctrl+Alt+Space 开/关的选区模式")
    print(mark_layer("emacs-mark"))
    print()
    print(";; 已知近似：")
    print(";;   1) alt 层的 ⌥, / ⌥. 输出 Ctrl+Home / Ctrl+End；⌥⇧, / ⌥⇧. 现在能分辨了，")
    print(";;      但仍归同一个输出（xremap 里只有 M-Shift-, 是 Ctrl+Home；要拆开说一声）。")
    print(";;   2) xremap 的 Ctrl_R-Shift-ro 那条没迁移（'ro' 不在你的键盘上，原本也不会触发）。")
    print(";;   3) mark 模式未实现 xremap 的 with_mark 自动清除；base 中物理左 Ctrl+Space 开关。")
    print(";;      mark 层本身可用 Space 关闭，窗口切层脚本也会重新选择基础层。")
    print(";;   4) meta 层逐键补 Ctrl，所以 ⌘+Shift+<其它键>（如 ⌘+Shift+Left）依旧是 Ctrl+Shift+Left。")
    print(";;   5) 按住 ⌘ 时持续保持左 Ctrl；鼠标、滚轮及 defsrc 外的键也能带 Ctrl。")
    print(";;   6) meta-editor 只改写 w，其余键仍是 Ctrl+X（与 meta 一致）。宏是「Ctrl+W 松开、再按 C」，")
    print(";;      编辑器端必须认得 ctrl-w 前缀（vim 模式的窗口前缀满足）；其它窗口走 meta，仍是纯 Ctrl+W。")


if __name__ == "__main__":
    main()
