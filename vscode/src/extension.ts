import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
	let disposable = vscode.commands.registerCommand("cont.helloWorld", () => {
		vscode.window.showInformationMessage("Hello World from cont!");
	});

	context.subscriptions.push(disposable);
}

export function deactivate() {}
