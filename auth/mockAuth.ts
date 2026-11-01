/** Authentication boundary. Replace with a configured provider before enabling account flows. */
export interface AuthUser { id: string; name: string; email: string }
export interface AuthResult { user?: AuthUser; error?: string }

const notConfigured: AuthResult = { error: 'Authentication is not connected yet. No account was created or signed in.' };
export async function mockSignIn(_email: string, _password: string): Promise<AuthResult> { return notConfigured; }
export async function mockSignUp(_name: string, _email: string, _password: string): Promise<AuthResult> { return notConfigured; }
