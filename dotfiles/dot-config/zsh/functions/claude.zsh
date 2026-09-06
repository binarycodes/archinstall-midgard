function _agent_run() {
    local tool="$1"
    local tag="$2"
    local workspace="$3"

    if [[ ! -d "$workspace" ]]; then
        printf 'usage: %s <workspace> [%s args...]\n' "$tool" "$tool" >&2
        return 1
    fi
    shift 3

    local workspace_abs name tmp_path
    local -a config cmd

    workspace_abs="$(cd "$workspace" && pwd -P)" || return 1
    # docker accepts a limited character set for --name
    # $RANDOM as well as the timestamp: two instances can start in the same
    # second, and $$ alone repeats when both are launched from one shell
    name="${tool}-$(basename "$workspace_abs")-$(date +%s)-${RANDOM}"
    name="${name//[^a-zA-Z0-9_.-]/-}"

    # Credentials and settings differ per CLI, so each gets its own volume.
    case "$tool" in
        claude)
            tmp_path="/tmp/agent-helper-${UID}"
            if [[ ! -f "${tmp_path}/claude.json" ]]; then
                mkdir -p "${tmp_path}"
                print '{}' > "${tmp_path}/claude.json"
            fi
            config=(
                -v claude_config:/home/agent/.claude
                -v "${tmp_path}/claude.json:/home/agent/.claude.json"
            )
            ;;
        codex)
            config=(-v codex_config:/home/agent/.codex)
            ;;
        gemini)
            config=(-v gemini_config:/home/agent/.gemini)
            ;;
    esac

    # Only an existing ~/.m2 is shared: a missing bind source would be created
    # root-owned by the daemon.
    local -a maven
    if [[ -d "$HOME/.m2" ]]; then
        maven=(-v "$HOME/.m2:/home/agent/.m2")
    fi

    cmd=(
        podman run
        --rm
        -it
        --pull always
        --userns keep-id:uid=1000,gid=1000
        --cap-drop ALL
        --security-opt no-new-privileges
        --pids-limit 4096
        --memory "${AGENT_MEMORY:-8g}"
        "${config[@]}"
        -v "${workspace_abs}:/workspace"
        "${maven[@]}"
        -v "${tool}_go:/home/agent/go"
        -v "${tool}_cache:/home/agent/.cache"
        -w /workspace
        -e JAVA_VERSION
        --name "$name"
        "docker.io/binarycodes/${tool}:${tag}"
        "$@" # forward extra args
    )

    "${cmd[@]}"
}

function claude() {
    _agent_run claude "${CLAUDE_IMAGE_TAG:-latest}" "$@"
}

function codex() {
    _agent_run codex "${CODEX_IMAGE_TAG:-latest}" "$@"
}

function gemini() {
    _agent_run gemini "${GEMINI_IMAGE_TAG:-latest}" "$@"
}
