import { NativeModule, registerWebModule } from 'expo';

class VeloVisionModule extends NativeModule<{}> {
  async analyzeVideo(_uri: string): Promise<string> {
    throw new Error('Apple Vision pose analysis is available in the iOS app build only.');
  }
}

export default registerWebModule(VeloVisionModule, 'VeloVision');
