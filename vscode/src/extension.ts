import * as vscode from "vscode";

import { spawn, ChildProcessWithoutNullStreams } from "child_process";

function handleCheckErrorsResponse(response_string: string, diagnostics: vscode.DiagnosticCollection) {
	let response = JSON.parse(response_string);
	if (!response.success) {
		if (response.display)
			vscode.window.showErrorMessage(response.error);
		else
			vscode.window.showErrorMessage(
				`Internal LSP error occured, please report it at https://github.com/farkon00/cont/issues.\n${response.error}`
			);
	} else if (response.has_error) {
		let pos = new vscode.Position(response.line, response.char);
		diagnostics.set(vscode.Uri.file(response.file), [new vscode.Diagnostic(
			new vscode.Range(pos, pos),
			response.error_message
		)]);
	} else {
		diagnostics.clear();
	}
}

function initLsp(): ChildProcessWithoutNullStreams | undefined {
	let path = vscode.workspace.getConfiguration().get("cont.lspLocation") as string;
	if (path) {
		console.log(`Starting cont lsp at ${path}`);
		let lsp = spawn("python3", [path]);
		lsp.stdout.setEncoding("utf-8");
		return lsp;
	} else {
		return undefined;
	}
}

export function activate(context: vscode.ExtensionContext) {
	// TODO: Update the process, when cont.lspLocation changes
	if (vscode.workspace.workspaceFolders)
		process.chdir(vscode.workspace.workspaceFolders[0].uri.fsPath);
		const diagnostics = vscode.languages.createDiagnosticCollection();
	let is_lsp_busy = false;
	let lsp = initLsp();
	context.subscriptions.push(
		vscode.workspace.onDidSaveTextDocument((e) => {
			if (e.languageId !== "cont") return;
			while (is_lsp_busy) {}
			if (!lsp) return;
			if (lsp.exitCode !== null)
				console.error(`Cont LSP process died with exit code ${lsp.exitCode}`)
			is_lsp_busy = true;
			lsp.stdin.write(JSON.stringify({
				type: "check_errors", file: e.fileName
			}) + "\n", function(error) {
				if (error) {
					console.error(error);
					return;
				}
				
				lsp?.stdout.once("data", function(data) {
					handleCheckErrorsResponse(data, diagnostics);
					is_lsp_busy = false;
				});
			});
		}
	));
	context.subscriptions.push(
		vscode.workspace.onDidChangeConfiguration((e) => {
			if (e.affectsConfiguration("cont.lspLocation")) {
				while (is_lsp_busy) {}
				is_lsp_busy = true;
				lsp = initLsp();
				is_lsp_busy = false;
			}
		})
	);
}
