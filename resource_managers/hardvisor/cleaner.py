

async def clean(remote_executor):
    await remote_executor.run(f"systemctl disable k3s k3s-agent --now")
    await remote_executor.run(f"rm -rf /var/lib/rancher/k3s/server/*")
    await remote_executor.run(f"curl -sfL https://get.k3s.io | sh -s - --cluster-reset --cluster-reset-restore-path=<path_to_snap> --cluster-init")
    await remote_executor.run(f"journalctl SYSLOG_IDENTIFIER=k3s --since '1 min ago' | grep 'restart without --cluster-reset'")
    await remote_executor.run(f"systemctl disable --now k3s")

