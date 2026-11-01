/** Local-only auth stub. Replace with a real provider before releasing account flows. */
export interface AuthUser { id: string; name: string; email: string }
export interface AuthResult { user?: AuthUser; error?: string }

const unavailable: AuthResult = { error: 'Authentication is not connected yet.' };
const demoUser = (name: string, email: string): AuthUser => ({
  id: 'velo-demo-user',
  name: name.trim() || email.trim().split('@')[0] || 'Velo Runner',
  email: email.trim() || 'runner@velo.demo',
});

export async function mockSignIn(email: string, _password: string): Promise<AuthResult> {
  return __DEV__ ? { user: demoUser('', email) } : unavailable;
}

export async function mockSignUp(name: string, email: string, _password: string): Promise<AuthResult> {
  return __DEV__ ? { user: demoUser(name, email) } : unavailable;
}
