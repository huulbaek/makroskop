import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { execSync } from 'node:child_process';

/** Short commit for the footer stamp: APP_COMMIT build arg (Docker) → git → '' (unknown). */
function gitShort(): string {
	if (process.env.APP_COMMIT) return process.env.APP_COMMIT.slice(0, 7);
	try {
		return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
	} catch {
		return '';
	}
}

export default defineConfig({
	define: {
		__APP_COMMIT__: JSON.stringify(gitShort()),
		__BUILD_DATE__: JSON.stringify(new Date().toISOString().slice(0, 10))
	},
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			adapter: adapter({ fallback: undefined })
		})
	]
});
